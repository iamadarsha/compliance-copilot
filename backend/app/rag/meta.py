"""Answers questions *about* the assistant and its corpus, before retrieval runs.

Someone opening this for the first time reasonably asks "what can you do?" or
"what circulars do you have?". Neither is a question about the circulars'
contents, so retrieval scores them terribly — measured 0.50 and 0.64 against a
0.69 threshold — and the app answers a newcomer's first question with a flat
refusal. That is a bad first impression created by an otherwise correct gate.

Two deliberate choices about how this is fixed:

1. It runs BEFORE retrieval and never calls a model. These answers are built
   from live `documents` rows, so the assistant cannot invent a circular it
   does not have, mis-state the count, or drift as the corpus changes. Letting
   an LLM answer "what documents do you have?" freely would put a hallucinated
   inventory in the one place this product cannot afford one.

2. Intent is matched by embedding similarity against canonical phrasings, not
   by keyword or regex rules. There are hundreds of ways to ask "what is this
   thing" and enumerating them as literals would be both endless and brittle —
   "what's in your database" and "where does your info come from" share no
   keywords but one intent. Embedding comparison generalises across phrasing
   using the model already loaded for retrieval, at no extra dependency.

The risk this introduces is hijacking: a genuine document question wrongly
treated as small talk. META_THRESHOLD is therefore set from measurement, with
the eval set used as the guard — no eval question may route here.
"""

from __future__ import annotations

import os

import numpy as np

from app.rag.embedder import embed_texts
from app.schemas import ComplianceAnswer

# Answered from the corpus itself; kept separate so each can be tuned and
# tested independently.
INTENT_ABOUT = "about"
INTENT_CORPUS = "corpus"

# Phrasings a first-time visitor actually uses. These are seeds for embedding
# comparison, not an exhaustive list to match literally — near-synonyms and
# unseen wordings are the point of doing this by similarity.
_CANONICAL: dict[str, list[str]] = {
    INTENT_ABOUT: [
        "what can you do",
        "what can you do for me",
        "how can you help me",
        "what are you",
        "who are you",
        "what is this",
        "what is this tool",
        "what is this platform about",
        "what is this app for",
        "what is the point of this",
        "why should I use this",
        "what can I ask you",
        "what kind of questions can you answer",
        "what topics do you cover",
        "what do you know about",
        "what can you tell me",
        "how do I use this",
        "help me get started",
    ],
    INTENT_CORPUS: [
        "what circulars do you have",
        "which circulars are indexed",
        "what documents do you have",
        "which documents are indexed",
        "list the circulars",
        "list your documents",
        "show me the documents",
        "how many circulars are there",
        "how many documents do you have",
        "what is in your database",
        "what sources do you use",
        "where does your information come from",
        "what are the circulars about",
        "what documents are loaded",
        "what have you indexed",
        "what regulations are covered",
        "which rules do you cover",
    ],
}

# Set from measurement, not intuition, and tuned the same way as the retrieval
# threshold: find the band between the two populations and sit in it.
#
# Measured over 15 meta phrasings and all 10 eval questions:
#   lowest meta score   0.7500  ("Hi" — short strings embed weakest)
#   highest eval score  0.6815  ("What is Milestone 2 ... MCX circular?" — it
#                                says "circular", so it reads closest to a
#                                corpus-inventory question without being one)
# Usable band (0.6815, 0.7500); 0.72 sits inside it, giving zero hijacks on
# the eval set. That eval ceiling is the number to re-check if the canonical
# phrasings ever grow — it is the closest a real question comes to this gate.
# Env-overridable so it can be swept without a rebuild.
META_THRESHOLD = float(os.environ.get("META_THRESHOLD", "0.72"))

_cached_vectors: dict[str, np.ndarray] | None = None


def _canonical_vectors() -> dict[str, np.ndarray]:
    """Embed the canonical phrasings once, on first use.

    Lazy rather than at import so module import stays free of model work —
    the embedder is already loaded at startup, but this keeps the cost on the
    first meta question rather than on every boot.
    """
    global _cached_vectors
    if _cached_vectors is None:
        _cached_vectors = {
            intent: np.array(embed_texts(phrasings))
            for intent, phrasings in _CANONICAL.items()
        }
    return _cached_vectors


def detect_intent(question: str) -> str | None:
    """Return the meta intent this question expresses, or None if it isn't one.

    Compares against every canonical phrasing and takes the best match. Both
    sides are embedded with `embed_texts` (no query prefix): this is a
    question-to-question comparison, not the question-to-passage matching the
    BGE query instruction is designed for.
    """
    text = question.strip()
    if not text:
        return None

    vector = np.array(embed_texts([text])[0])
    best_intent, best_score = None, 0.0
    for intent, canonical in _canonical_vectors().items():
        # Vectors are already L2-normalised by the embedder, so the dot
        # product is the cosine similarity.
        score = float(np.max(canonical @ vector))
        if score > best_score:
            best_intent, best_score = intent, score

    return best_intent if best_score >= META_THRESHOLD else None


def _format_date(iso: str) -> str:
    year, month, day = iso.split("-")
    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    return f"{day} {months[int(month) - 1]} {year}"


def _short_issuer(issuer: str) -> str:
    for short in ("SEBI", "NSE", "MCX"):
        if short in issuer:
            return short
    return issuer.split(",")[0].strip()


def build_answer(intent: str, documents: list[dict]) -> ComplianceAnswer:
    """Build the response for a meta intent from live document rows.

    `refused=False` with an empty citation list is correct and deliberate here:
    the answer is true and useful, but it describes the assistant rather than
    quoting a circular, so there is nothing to cite. These never pass through
    the generator, so the citation-consistency check — which would otherwise
    read "no primary citation" as an inconsistency — never applies.
    """
    count = len(documents)
    issuers = sorted({_short_issuer(d["issuer"]) for d in documents})

    if intent == INTENT_CORPUS:
        lines = [
            f"- {_format_date(str(d['doc_date']))} — {_short_issuer(d['issuer'])} — {d['title']}"
            for d in documents
        ]
        span = ""
        if count:
            span = (
                f", spanning {_format_date(str(documents[0]['doc_date']))} to "
                f"{_format_date(str(documents[-1]['doc_date']))}"
            )
        body = (
            f"I have {count} circulars indexed{span}. They are issued by "
            f"{', '.join(issuers)} and all concern retail participation in algorithmic "
            "trading:\n\n" + "\n".join(lines) + "\n\n"
            "You can ask about anything these documents actually state — thresholds, "
            "deadlines, registration steps, security requirements. The panel beside "
            "this answer links to each source document."
        )
    else:
        body = (
            "I answer questions about Indian securities-market circulars on retail "
            "algorithmic trading — the SEBI, NSE and MCX rules covering how retail "
            "investors may use trading algorithms and broker APIs.\n\n"
            "Things worth asking:\n"
            "- What is the maximum order-per-second threshold before an algo must be registered?\n"
            "- How often can a client update their mapped static IP address?\n"
            "- What is Milestone 2 for stock brokers according to the MCX circular?\n"
            "- Who counts as 'family' for sharing a registered algo?\n\n"
            f"Every answer comes from {count} indexed circulars and is cited to a specific "
            "document and section. When the documents do not cover something, I say so "
            "instead of guessing — so a refusal usually means the rule genuinely is not in "
            "this document set, not that the question was misunderstood.\n\n"
            "Ask \"what circulars do you have?\" to see the full list."
        )

    return ComplianceAnswer(answer=body, citations=[], confidence="high", refused=False)

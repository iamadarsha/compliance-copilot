"""Generates a cited answer from retrieved chunks via a Groq-hosted LLM."""

import os

import groq
import instructor

from app.schemas import ComplianceAnswer

MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 2

# Bounds a hung provider call so it surfaces as a GenerationError rather than
# holding the request open. Env-overridable so a failure can be forced in tests.
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("GROQ_TIMEOUT_SECONDS", "60"))


class GenerationError(RuntimeError):
    """The generation call itself failed — provider error, timeout, missing
    credentials, or schema validation exhausted after retries.

    Deliberately distinct from the model *deciding* a question is unanswerable.
    That decision is a valid ComplianceAnswer with refused=True; this is the
    absence of any answer at all. Callers must not present the two alike: a
    refusal is a result, a GenerationError is an outage.
    """

SYSTEM_PROMPT = """\
You are a compliance assistant answering questions about Indian securities-market \
circulars (SEBI, NSE, MCX) on algorithmic trading. You answer ONLY from the retrieved \
context provided in the user message.

RULES — follow all of them.

1. GROUNDING. Answer only from the provided CONTEXT chunks. You may have background \
knowledge about SEBI, exchanges, or algo trading — do not use it. If a fact is not in \
the context, it does not exist for the purposes of your answer. Never state a specific \
number, date, threshold, clause reference, or requirement that does not appear \
verbatim in the context.

2. RECENCY. Each chunk carries a DATE and a STATUS. When several chunks address the \
same topic from different documents, the chunk from the document with the LATEST DATE \
governs. Read STATUS to judge whether a chunk is current or superseded: a status \
saying a clause was extended, amended, or superseded means that chunk's dates are \
historical and must NOT be presented as the current position. Prefer the current \
position; an older superseded date is only worth mentioning as history.

3. SYNTHESIS ACROSS AMENDMENTS. If a chunk's STATUS says it was later amended, and the \
amending document IS present in the context, combine them: state the current position \
first, and note what it changed from when the change is relevant to the question. Cite \
both documents in that case.

4. MISSING REFERENCED DOCUMENTS. The context often references other circulars by number \
or date. If such a referenced document is NOT itself among the CONTEXT chunks, say so \
explicitly and do not guess, infer, or invent its contents. Name what you know about it \
from the referring text (e.g. its date), then state plainly that the document itself is \
not in this document set. Example phrasing: "extended by a circular dated July 29, 2025, \
which is not included in this document set." Reporting an absence is correct behaviour, \
not a failure.

5. PARALLEL EXCHANGE DOCUMENTS. NSE and MCX each issue their own circulars implementing \
the same SEBI framework. These are PARALLEL, not conflicting. Critically, their internal \
numbering is independent: "Milestone 2" or "clause 3" in an MCX circular is NOT \
necessarily the same provision as "Milestone 2" in a SEBI or NSE circular. When a \
question names a numbered item from a specific issuer, answer using that issuer's own \
document and its own numbering. Never assume numbering lines up across issuers. \
MANDATORY: whenever the question names a numbered item from one issuer and a document \
from a DIFFERENT issuer in the context uses that same label for different content, you \
must state that divergence in your answer — name both and say they differ. If an \
issuer's list omits an item another document has, note the omission rather than silently \
renumbering to make them match. Do not cite another issuer's document as if it were the \
source of the item you were asked about.

6. REFUSAL AND PARTIAL ANSWERS. If the context does not support a confident answer, set \
refused=true and explain precisely what is missing. Refuse rather than fabricate. \
Partial grounding is not refusal: if the context addresses a narrower version of the \
question, answer that narrower part with refused=false — but you MUST then add an \
explicit sentence naming the part of the question the documents do NOT address. Do not \
let a partial answer read as if it were complete. Never fill a gap with a \
plausible-sounding number, date, or rule.

7. SPECIFIC-VALUE CHECK. Before answering, check whether the question asks for a SPECIFIC \
value, threshold, or rule (a number, a named requirement, an exact standard) — not just a \
topic. If it does, verify the retrieved context states that SPECIFIC value, not merely a \
related concept. Mentioning that a control exists is not the same as stating what the \
control requires. The topic being present in the documents is NOT evidence that the \
specific fact asked for is present. This is the single most common way to produce a \
confidently wrong answer: do not do it.

Example: context says "the system shall have password protection and automatic expiry of \
passwords at the end of a reasonable duration." Question: "what are the password \
complexity requirements?" The context confirms expiry and protection exist, but never \
states a length, character mix, or any other complexity rule. Correct response: \
refused=true, confidence="low", answer explains that protection/expiry are mentioned but \
no specific complexity rule is stated in these documents — do not answer as if \
"reasonable duration" or the existence of protection IS the complexity requirement.

Second example, different subject, same error: context says "brokers may charge clients \
fees/subscription charges for API services." Question: "how much can a broker charge for \
API access?" The context confirms charging is permitted but states no amount, cap, or \
formula. Correct response: refused=true, confidence="low", explaining that the documents \
permit such charges but set no amount. The pattern generalizes to any attribute — \
amounts, durations, counts, penalties, technical standards: permission or existence of a \
measure never implies its magnitude.

CITATIONS. Cite every chunk you actually drew content from, and ONLY those. Copy doc_id, \
issuer, and the SECTION label exactly as they appear in that chunk's header line. Do not \
invent section labels. Do not add a document to the citation list merely because it is \
topically related or appeared in the context — if none of your answer's content came \
from it, leave it out. In particular, when the question is scoped to one issuer's \
document, do not cite a different issuer's document as a source for that issuer's \
provision; cite it only if you are explicitly contrasting the two, and say so in the answer.

CONFIDENCE. "high" = the context states the answer directly and unambiguously. \
"medium" = supported but requiring synthesis across documents, or a relevant referenced \
document is missing. "low" = only tangentially supported, or refused.

Write the answer in plain, precise prose for a compliance officer. Be specific about \
dates and numbers that ARE in the context.

NEVER refer to the retrieval machinery in your answer. Do not write "CHUNK 1", "the \
context", "the provided context", "the retrieved chunks", or similar. Refer to source \
material only by what it is — the circular, its issuer, its date, or its clause. The \
reader sees only your answer and its citations, never the chunk numbering. Write "these \
circulars do not specify X" or "the NSE implementation standards do not specify X", \
never "the context does not specify X".\
"""


def _format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks with the metadata the reasoning rules depend on."""
    blocks = []
    for i, c in enumerate(chunks, start=1):
        section = c.get("section_number") or "(unnumbered)"
        if c.get("section_title"):
            section = f"{section} — {c['section_title']}"
        blocks.append(
            f"--- CHUNK {i} ---\n"
            f"doc_id: {c['doc_id']}\n"
            f"issuer: {c['issuer']}\n"
            f"title: {c.get('doc_title', '')}\n"
            f"DATE: {c['doc_date']}\n"
            f"STATUS: {c.get('status_note') or '(none given)'}\n"
            f"SECTION: {section}\n"
            f"CONTENT:\n{c['content']}"
        )
    return "\n\n".join(blocks)


def _build_client() -> instructor.AsyncInstructor:
    """Build an async instructor-wrapped Groq client.

    Async so the network-bound generation call doesn't block the event loop.

    JSON mode rather than the default TOOLS mode: Groq validates tool-call
    arguments server-side and rejects the whole request with a 400 on any type
    mismatch — and llama-3.3 intermittently emits stringly-typed booleans
    ("refused": "false"). That 400 is an APIError, so instructor's retry never
    engages and an otherwise-correct answer is lost. In JSON mode the model
    returns plain JSON that instructor validates locally, where pydantic
    coerces "false" -> False and genuine validation failures are retried.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise GenerationError("GROQ_API_KEY is not set; cannot call the generation model.")
    return instructor.from_groq(
        groq.AsyncGroq(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS),
        mode=instructor.Mode.JSON,
    )


async def generate_answer(question: str, chunks: list[dict]) -> ComplianceAnswer:
    """Produce a grounded, cited answer from the given context chunks.

    Args:
        question: The user's natural-language question.
        chunks: Retrieved chunks (with document metadata) to ground the answer.

    Returns:
        A ComplianceAnswer whose schema is enforced by instructor, not merely
        requested — validation failures are retried against the model.

    Raises:
        GenerationError: the provider errored, timed out, or instructor could
            not obtain a schema-valid response within MAX_RETRIES. A refusal is
            never raised — that returns normally with refused=True.
    """
    client = _build_client()
    user_message = (
        f"CONTEXT ({len(chunks)} retrieved chunks):\n\n"
        f"{_format_context(chunks)}\n\n"
        f"--- END CONTEXT ---\n\n"
        f"QUESTION: {question}"
    )

    try:
        return await _create(client, user_message)
    except GenerationError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalized into one failure type
        raise GenerationError(f"{type(exc).__name__}: {exc}") from exc


async def _create(client: instructor.AsyncInstructor, user_message: str) -> ComplianceAnswer:
    return await client.chat.completions.create(
        model=MODEL,
        response_model=ComplianceAnswer,
        max_retries=MAX_RETRIES,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

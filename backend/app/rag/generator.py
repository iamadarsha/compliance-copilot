"""Generates a cited answer from retrieved chunks, with provider failover.

Gemini is the primary generator and Groq the fallback. Failover is triggered
ONLY by a GenerationError — a provider-level fault. A model that successfully
returns refused=True has done its job correctly and that answer is returned
as-is; retrying another provider in the hope of a non-refusal would be
shopping for the answer we wanted, which in a compliance tool is precisely
the failure mode the refusal logic exists to prevent.
"""

import asyncio
import logging
import os
import time
from typing import NamedTuple

import groq
import instructor

from app.schemas import ComplianceAnswer

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"

# Gemini cascade, tried in order before falling back to Groq. Every ID here was
# checked against ai.google.dev's models/deprecations/pricing pages rather than
# recalled — note there is NO "gemini-3.1-flash"; that generation ships only a
# -lite flash variant, so it is absent by fact, not oversight.
#
# Ordering is cheapest-and-current first, then the same generation's fuller
# model, then older generations. The premium 3.7/3.6 flash models are
# deliberately excluded: the brief asks for small, cheap models, and a failover
# path is the worst place to silently start spending more per query.
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",  # current fast/cheap tier, no announced shutdown
    "gemini-3.5-flash",  # same generation, more headroom
    "gemini-3.1-flash-lite",  # older gen; retires 2027-05-07
    "gemini-2.5-flash-lite",  # cheapest overall ($0.10/$0.40 per 1M)
    "gemini-2.5-flash",  # 2.5 line is NOT deprecated; 2.0 was
]
GEMINI_MODEL = GEMINI_MODELS[0]

# Hard ceiling on the entire Gemini stage, independent of how many models are
# left to try. This is what keeps the cascade a failsafe rather than a new
# source of latency: once the budget is spent the remaining models are skipped
# and Groq — which is fast and already proven on this workload — takes over.
# In practice the cascade gets through 1-2 models before handing off.
GEMINI_TOTAL_BUDGET_SECONDS = float(os.environ.get("GEMINI_TOTAL_BUDGET_SECONDS", "25"))

# Substrings marking a failure that will recur identically on every Gemini
# model — a bad/absent credential, or the API not being enabled for the
# project. Cascading through five models on one of these just multiplies the
# same rejection, so the cascade short-circuits straight to Groq. Matching on
# message text is admittedly brittle; it fails safe, since an unrecognised
# error simply falls through to the normal per-model cascade.
_GEMINI_FATAL_MARKERS = (
    "api key not valid",
    "api_key_invalid",
    "unauthenticated",
    "permission_denied",
    "permission denied",
    "consumer_suspended",
    "has not been used in project",
    "401",
    "403",
    # Client-side misconfiguration (e.g. a missing optional dependency) is
    # every bit as model-independent as a bad credential. Learned the hard
    # way: a missing `jsonref` made all five models fail in turn, four of
    # those attempts pure waste.
    "configurationerror",
)

# Provider labels recorded against each query so it's visible after the fact
# which provider actually served it.
GROQ_PROVIDER = f"groq/{GROQ_MODEL}"
GEMINI_PROVIDER = f"gemini/{GEMINI_MODEL}"

# Kept for backwards compatibility with anything still importing MODEL.
MODEL = GROQ_MODEL

MAX_RETRIES = 2

# Bounds a hung provider call so it surfaces as a GenerationError rather than
# holding the request open. Env-overridable so a failure can be forced in tests.
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("GROQ_TIMEOUT_SECONDS", "60"))

# Deliberately tight. A flash-lite answer on this corpus lands in a couple of
# seconds, so 15s already means something is wrong — waiting the full 60s a
# generous timeout would allow just delays the fallback that is going to be
# needed anyway. Failing fast is the point of having a fallback at all.
GEMINI_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "15"))

# instructor's from_provider() selects the recommended mode per provider, and
# its own docs advise letting it. Groq needed an explicit override (see
# _build_groq_client) but that finding is Groq-specific — it was about Groq
# validating tool-call arguments server-side — and does not transfer to
# Gemini, which has native structured-output support. Left on auto-select,
# overridable via env purely so the choice can be A/B tested without a rebuild.
_GEMINI_MODE_OVERRIDE = os.environ.get("GEMINI_MODE", "").strip().upper()


class GenerationError(RuntimeError):
    """The generation call itself failed — provider error, timeout, missing
    credentials, or schema validation exhausted after retries.

    Deliberately distinct from the model *deciding* a question is unanswerable.
    That decision is a valid ComplianceAnswer with refused=True; this is the
    absence of any answer at all. Callers must not present the two alike: a
    refusal is a result, a GenerationError is an outage.
    """


class GenerationResult(NamedTuple):
    """An answer plus the provider that actually produced it.

    generate() returns this rather than a bare ComplianceAnswer so the caller
    can log which provider served the request. The alternative — stashing the
    provider in module state — would race under concurrent requests and report
    the wrong provider for a query, which is worse than useless in a log meant
    for reliability debugging.
    """

    answer: ComplianceAnswer
    provider: str

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

Each citation also carries a ROLE. Mark it "primary" if that chunk directly states the \
specific fact, value, or rule the question asked for. Mark it "contrast" if the chunk is \
genuinely on-topic and worth citing but does NOT itself supply that specific value — the \
password-protection example in rule 7 is exactly this case: a chunk confirming that \
password protection and expiry exist is "contrast" for a question about complexity \
requirements, because it establishes the topic without stating the requirement asked for. \
Never mark a citation "primary" merely because it is topically related. If every citation \
you would give for an answer is "contrast" — none of them state the specific thing asked \
— that is the same signal as rule 7's specific-value check and means refused must be true, \
not false. A "contrast"-only citation list is not evidence that you have answered the \
question; it is evidence that you have not.

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


def _build_user_message(question: str, chunks: list[dict]) -> str:
    """The single user-message shape both providers receive.

    Shared deliberately: the whole point of the failover is that the fallback
    answers the same question from the same evidence under the same rules. Any
    divergence here would make the two providers quietly non-equivalent.
    """
    return (
        f"CONTEXT ({len(chunks)} retrieved chunks):\n\n"
        f"{_format_context(chunks)}\n\n"
        f"--- END CONTEXT ---\n\n"
        f"QUESTION: {question}"
    )


def _build_groq_client() -> instructor.AsyncInstructor:
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


def _build_gemini_client(model: str) -> instructor.AsyncInstructor:
    """Build an async instructor-wrapped Gemini client for one model."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise GenerationError("GEMINI_API_KEY is not set; cannot call the primary model.")
    kwargs: dict = {"async_client": True, "api_key": api_key}
    if _GEMINI_MODE_OVERRIDE:
        kwargs["mode"] = getattr(instructor.Mode, _GEMINI_MODE_OVERRIDE)
    return instructor.from_provider(f"google/{model}", **kwargs)


def _is_fatal_for_all_gemini(exc: Exception) -> bool:
    """Whether this failure would recur identically on every other Gemini model."""
    message = str(exc).lower()
    return any(marker in message for marker in _GEMINI_FATAL_MARKERS)


async def _create(
    client: instructor.AsyncInstructor, model: str, user_message: str
) -> ComplianceAnswer:
    return await client.chat.completions.create(
        model=model,
        response_model=ComplianceAnswer,
        max_retries=MAX_RETRIES,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )


async def generate_groq(question: str, chunks: list[dict]) -> ComplianceAnswer:
    """Answer via Groq. Raises GenerationError on any provider-level failure."""
    client = _build_groq_client()
    try:
        return await _create(client, GROQ_MODEL, _build_user_message(question, chunks))
    except GenerationError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalized into one failure type
        raise GenerationError(f"{type(exc).__name__}: {exc}") from exc


async def generate_gemini(
    question: str, chunks: list[dict], model: str = GEMINI_MODEL
) -> ComplianceAnswer:
    """Answer via one Gemini model. Raises GenerationError on provider failure.

    The call is wrapped in a hard asyncio timeout rather than relying on the
    SDK's own: it bounds the request provider-agnostically, and gives a clean
    lever (GEMINI_TIMEOUT_SECONDS) for exercising the failover path in tests
    without needing to invalidate a real credential.
    """
    client = _build_gemini_client(model)
    try:
        return await asyncio.wait_for(
            _create(client, model, _build_user_message(question, chunks)),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except GenerationError:
        raise
    except TimeoutError as exc:
        raise GenerationError(f"timed out after {GEMINI_TIMEOUT_SECONDS}s") from exc
    except Exception as exc:  # noqa: BLE001 - normalized into one failure type
        raise GenerationError(f"{type(exc).__name__}: {exc}") from exc


async def generate_gemini_cascade(question: str, chunks: list[dict]) -> GenerationResult:
    """Try each Gemini model in turn, newest/cheapest first.

    Cascading across models is worth doing because the realistic Gemini failure
    is per-model, not account-wide: quota is metered per model, and an
    individual model can be overloaded or retired while its siblings are fine.
    It is NOT worth doing for a bad credential, which every model rejects
    identically — hence the fatal-error short-circuit.

    Bounded twice over (per-model timeout and a total stage budget) so that a
    slow cascade can never cost more than going straight to the fallback would
    have saved.

    Raises:
        GenerationError: every Gemini model failed, the budget ran out, or the
            first failure was one that all models would share.
    """
    stage_started = time.monotonic()
    last_error: Exception | None = None

    for index, model in enumerate(GEMINI_MODELS):
        elapsed = time.monotonic() - stage_started
        if index > 0 and elapsed >= GEMINI_TOTAL_BUDGET_SECONDS:
            logger.warning(
                "Gemini stage budget of %.0fs exhausted after %.1fs; skipping "
                "remaining %d model(s) and handing off",
                GEMINI_TOTAL_BUDGET_SECONDS,
                elapsed,
                len(GEMINI_MODELS) - index,
            )
            break

        try:
            answer = await generate_gemini(question, chunks, model)
        except GenerationError as exc:
            last_error = exc
            if _is_fatal_for_all_gemini(exc):
                logger.warning(
                    "gemini/%s failed with an account-level fault (%s); skipping the "
                    "remaining Gemini models since they would fail identically",
                    model,
                    exc,
                )
                break
            logger.warning("gemini/%s failed (%s); trying next Gemini model", model, exc)
            continue

        if index > 0:
            logger.info("gemini/%s served the request after %d earlier failure(s)", model, index)
        return GenerationResult(answer, f"gemini/{model}")

    raise GenerationError(f"all Gemini models failed; last error: {last_error}")


def _enforce_citation_consistency(answer: ComplianceAnswer) -> ComplianceAnswer:
    """Structural backstop: refused=false with no primary citation is a
    self-contradictory answer, corrected here rather than trusted.

    Provider-agnostic and prose-free by construction — it reads only the
    structured `role` field, never the answer text. Found via q5 (the
    password-complexity question): Gemini set refused=false/confidence=high
    while citing only a chunk that confirmed the topic without stating the
    value asked for. An empty citations list fails the same check (any() over
    [] is False), so this one rule also covers that simpler failure mode
    without a separate empty-list branch.
    """
    if answer.refused:
        return answer
    if any(c.role == "primary" for c in answer.citations):
        return answer

    logger.warning(
        "refused=false with no primary citation (%d citation(s), all contrast); "
        "forcing refused=True",
        len(answer.citations),
    )
    return answer.model_copy(
        update={
            "refused": True,
            "confidence": "low",
            "answer": answer.answer
            + "\n\n(Note: no supporting citation was returned for this answer — "
            "treat with caution.)",
        }
    )


async def generate(question: str, chunks: list[dict]) -> GenerationResult:
    """Produce a grounded, cited answer, falling back across providers.

    Gemini first; on GenerationError, log the cause and try Groq. If Groq also
    raises, the error propagates so the router's existing 503 path handles it.

    A successful answer is returned unconditionally — including one with
    refused=True. A refusal is a valid, correct result, not a failure signal:
    failing over on refusal would mean re-rolling the question against a second
    model until one agreed to answer, which is exactly the behaviour the
    grounding rules are designed to prevent.

    Raises:
        GenerationError: both providers failed at the provider level.
    """
    try:
        gemini_result = await generate_gemini_cascade(question, chunks)
        return GenerationResult(
            _enforce_citation_consistency(gemini_result.answer), gemini_result.provider
        )
    except GenerationError as gemini_exc:
        logger.warning(
            "Every Gemini model failed (%s); falling back to %s",
            gemini_exc,
            GROQ_PROVIDER,
        )
        try:
            answer = await generate_groq(question, chunks)
        except GenerationError as groq_exc:
            logger.error(
                "Fallback provider %s also failed (%s); no answer available",
                GROQ_PROVIDER,
                groq_exc,
            )
            raise
        logger.info("Fallback provider %s served the request", GROQ_PROVIDER)
        return GenerationResult(_enforce_citation_consistency(answer), GROQ_PROVIDER)


async def generate_answer(question: str, chunks: list[dict]) -> ComplianceAnswer:
    """Backwards-compatible wrapper returning just the answer."""
    result = await generate(question, chunks)
    return result.answer

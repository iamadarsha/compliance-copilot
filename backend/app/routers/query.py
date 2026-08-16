"""Endpoints for answering compliance questions via retrieval-augmented generation."""

import json
import os
import time

from fastapi import APIRouter, HTTPException

from app.db.session import get_pool
from app.rag import generator, meta
from app.rag.retriever import retrieve_chunks
from app.routers.documents import fetch_documents
from app.schemas import ComplianceAnswer, QueryRequest, QueryResponse


def _with_diagnostics(
    answer: ComplianceAnswer,
    *,
    top_similarity: float | None,
    provider: str | None,
    refusal_reason: str | None,
    latency_ms: int,
) -> QueryResponse:
    """Attach how-it-was-produced metadata to an answer for the response body.

    Same values already written to the `queries` table — returned as well so the
    behaviour is checkable from the client without database access.
    """
    return QueryResponse(
        **answer.model_dump(),
        top_similarity=round(top_similarity, 4) if top_similarity is not None else None,
        provider=provider,
        refusal_reason=refusal_reason,
        latency_ms=latency_ms,
    )

router = APIRouter(prefix="/query", tags=["query"])

# Layer 1 refusal gate. Below this top cosine similarity we never reach the
# model at all. 0.69 was tuned empirically in Phase 5's eval: the lowest
# genuinely answerable question in the test set scores 0.728 (a hard ceiling —
# anything higher starts blocking real questions), and the two measured
# out-of-domain distractors score 0.615/0.651, so 0.69 sits in the gap between
# them. 0.5 (the original placeholder) was verified to catch nothing at all.
# Env-overridable so Phase 5's eval can sweep it without a rebuild.
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.69"))

# Values recorded in the stored query's answer_json so evaluation can tell the
# refusal paths apart. `None` means the model answered without refusing.
REFUSAL_BELOW_THRESHOLD = "below_threshold"
REFUSAL_MODEL = "model_refused"
REFUSAL_GENERATION_ERROR = "generation_error"

# Recorded as the "provider" for meta answers. Deliberately not a model name:
# nothing generated these, so labelling them with one would misreport how the
# answer was produced in exactly the log built to keep that honest.
META_PROVIDER = "meta/deterministic"


async def _insert_query(question: str, payload: dict, model: str | None, latency_ms: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO queries (question, answer_json, model, latency_ms)
            VALUES ($1, $2::jsonb, $3, $4)
            """,
            question,
            json.dumps(payload),
            model,
            latency_ms,
        )


async def _log_query(
    question: str,
    answer: ComplianceAnswer,
    model: str | None,
    latency_ms: int,
    refusal_reason: str | None,
    top_similarity: float,
    provider: str | None = None,
) -> None:
    """Persist the answered question to `queries` for evaluation and debugging.

    `provider` records which generation provider actually served the request —
    with failover in play, "which model answered this?" is no longer inferable
    from configuration alone and has to be captured per query.
    """
    payload = answer.model_dump()
    payload["refusal_reason"] = refusal_reason
    payload["top_similarity"] = round(top_similarity, 4)
    payload["provider"] = provider
    await _insert_query(question, payload, model, latency_ms)


async def _log_generation_failure(
    question: str,
    detail: str,
    model: str | None,
    latency_ms: int,
    top_similarity: float,
) -> None:
    """Record a failed generation.

    Stored under refusal_reason="generation_error" exactly as before, so the
    eval can still separate provider failures from real refusals. The provider
    message is kept in a dedicated `error` key — never in `answer` — because
    `answer` is what a client renders, and an outage must not be dressed up as
    a refusal. answer/confidence/refused are null: no decision was ever made.
    """
    payload = {
        "answer": None,
        "citations": [],
        "confidence": None,
        "refused": None,
        "refusal_reason": REFUSAL_GENERATION_ERROR,
        "top_similarity": round(top_similarity, 4),
        "error": detail,
    }
    await _insert_query(question, payload, model, latency_ms)


@router.post("", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Answer a question by retrieving relevant chunks and generating a cited response.

    Two-layer refusal gate:
      * Layer 1 (here, deterministic): if the best retrieved chunk scores below
        SIMILARITY_THRESHOLD, skip the model entirely and refuse.
      * Layer 2 (in the model, per the system prompt): chunks that clear the
        threshold but still don't support an answer make the model itself refuse.
    """
    started = time.perf_counter()
    chunks, top_similarity = await retrieve_chunks(request.question)

    # --- Layer 1: deterministic threshold gate ---
    if top_similarity < SIMILARITY_THRESHOLD:
        # Before refusing, check whether this is a question about the assistant
        # itself — "what can you do?", "what circulars do you have?". Those are
        # not questions about document *contents*, so they score 0.50-0.66 here
        # and would otherwise get a flat refusal as a newcomer's first
        # interaction. Answered deterministically from the documents table, so
        # the assistant can never claim a circular it does not hold.
        #
        # Deliberately placed INSIDE the below-threshold branch rather than
        # before retrieval, which is where it was first written and was wrong:
        # ahead of retrieval it stole questions the documents could answer well.
        # "MCX circular" (retrieval 0.77) and "22 Jul 2025 circular summary"
        # (0.75) both matched a corpus-inventory phrasing and got a list of
        # documents instead of an answer. Short, keyword-style queries embed
        # weakly and drift toward the generic canonical phrasings, which a test
        # set made only of well-formed questions never surfaced.
        #
        # Here, meta can only ever claim a question that was already going to be
        # refused, so hijacking a real answer is structurally impossible rather
        # than merely tuned against.
        intent = meta.detect_intent(request.question)
        if intent is not None:
            documents = await fetch_documents()
            answer = meta.build_answer(intent, documents)
            latency_ms = int((time.perf_counter() - started) * 1000)
            await _log_query(
                request.question,
                answer,
                META_PROVIDER,
                latency_ms,
                None,
                top_similarity,
                META_PROVIDER,
            )
            return _with_diagnostics(
                answer,
                top_similarity=top_similarity,
                provider=META_PROVIDER,
                refusal_reason=None,
                latency_ms=latency_ms,
            )

        answer = ComplianceAnswer(
            answer=(
                "I don't have sufficiently relevant material in this document set to answer that. "
                "The closest passage retrieved scored "
                f"{top_similarity:.2f} similarity, below the {SIMILARITY_THRESHOLD:.2f} threshold "
                "required to attempt an answer. This document set covers SEBI, NSE and MCX circulars "
                "on retail participation in algorithmic trading."
            ),
            citations=[],
            confidence="low",
            refused=True,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _log_query(
            request.question, answer, None, latency_ms, REFUSAL_BELOW_THRESHOLD, top_similarity
        )
        return _with_diagnostics(
            answer,
            top_similarity=top_similarity,
            provider=None,
            refusal_reason=REFUSAL_BELOW_THRESHOLD,
            latency_ms=latency_ms,
        )

    # --- Layer 2: model-level grounding and refusal ---
    # generate() tries Gemini, then falls back to Groq on a provider fault only;
    # it returns the provider that actually served the request so it can be
    # logged. A model's own refusal never triggers failover — see generator.generate.
    model_name: str | None = None
    provider: str | None = None
    try:
        answer, provider = await generator.generate(request.question, chunks)
        model_name = provider
    except generator.GenerationError as exc:
        # An outage, not an answer. Returning 200 here would make a provider
        # failure indistinguishable from a refusal to every consumer — which is
        # exactly how a 429 ended up rendered as "not covered by these
        # documents". Fail loudly with 503 and keep the provider text out of
        # the response body.
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _log_generation_failure(
            request.question, str(exc), model_name, latency_ms, top_similarity
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "generation_unavailable",
                "message": (
                    "The answer could not be generated because the generation service is "
                    "temporarily unavailable. This is a service fault, not a determination "
                    "about the documents. Please retry."
                ),
            },
        ) from exc

    refusal_reason = REFUSAL_MODEL if answer.refused else None
    latency_ms = int((time.perf_counter() - started) * 1000)
    await _log_query(
        request.question,
        answer,
        model_name,
        latency_ms,
        refusal_reason,
        top_similarity,
        provider,
    )
    return _with_diagnostics(
        answer,
        top_similarity=top_similarity,
        provider=provider,
        refusal_reason=refusal_reason,
        latency_ms=latency_ms,
    )

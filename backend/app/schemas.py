"""Pydantic request/response models shared across routers."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DocumentBase(BaseModel):
    doc_id: str
    title: str
    issuer: str
    doc_date: date
    status_note: str | None = None
    source_url: str | None = None
    filename: str


class DocumentOut(DocumentBase):
    id: int

    class Config:
        from_attributes = True


class ChunkOut(BaseModel):
    id: int
    document_id: int
    section_number: str | None = None
    section_title: str | None = None
    content: str

    class Config:
        from_attributes = True


class DocumentChunkCount(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class IngestResponse(BaseModel):
    documents_ingested: int
    total_chunks: int
    chunks_per_document: list[DocumentChunkCount]


class QueryRequest(BaseModel):
    # No length bound at all was a real gap: an oversized question inflates
    # every downstream Groq call's token cost (the raw question text goes
    # straight into the prompt), and nothing server-side rejected a request
    # sent directly to the API (bypassing the frontend's .trim() check) with
    # an empty or whitespace-only question. 500 chars comfortably covers any
    # real compliance question — the longest in the eval set is ~140.
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty or whitespace-only")
        return value


class Citation(BaseModel):
    doc_id: str = Field(description="The doc_id of the source document, copied exactly as given in the context.")
    issuer: str = Field(description="The issuer of the source document, copied exactly as given in the context.")
    section: str = Field(
        description="The section label of the chunk used, copied exactly from its SECTION field (e.g. '7', 'B', 'Annexure')."
    )
    role: Literal["primary", "contrast"] = Field(
        description=(
            "'primary' if this chunk directly states the specific fact, value, or rule the "
            "question asked for. 'contrast' if the chunk is genuinely on-topic and worth "
            "citing but does NOT itself supply that specific value — e.g. it confirms a "
            "control exists without giving the control's parameters. Never mark a citation "
            "'primary' merely because it is topically related to the question."
        )
    )


class ComplianceAnswer(BaseModel):
    answer: str = Field(description="The answer, grounded strictly in the provided context chunks.")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Every chunk actually relied on for the answer. Empty only when refusing with nothing usable.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "high: context states the answer directly and unambiguously. "
            "medium: context supports the answer but requires synthesis across documents, "
            "or a relevant referenced document is missing. "
            "low: context is only tangentially related, or the answer is refused."
        )
    )
    refused: bool = Field(
        description="True when the context does not support a confident answer. Then `answer` must explain what is missing."
    )


class QueryResponse(ComplianceAnswer):
    """What `/query` returns: the model's answer plus how it was produced.

    Deliberately a separate model rather than extra fields on ComplianceAnswer.
    ComplianceAnswer is the schema instructor enforces on the *model* — adding
    server-computed fields to it would ask the LLM to invent its own retrieval
    score and latency, which is both nonsense and a fabrication risk.

    These four values were already computed and written to the `queries` table
    on every request; they were simply never returned. Surfacing them is what
    makes the pipeline's behaviour checkable from outside: whether a refusal
    came from the deterministic threshold or the model's own judgment, which
    provider actually served the answer, and how close the retrieved material
    was to the question.
    """

    top_similarity: float | None = Field(
        default=None,
        description="Cosine similarity of the best-matching chunk. None when retrieval was skipped.",
    )
    provider: str | None = Field(
        default=None,
        description=(
            "What produced this answer: 'gemini/<model>', 'groq/<model>', or "
            "'meta/deterministic'. None for a Layer-1 refusal, which never reaches a model."
        ),
    )
    refusal_reason: str | None = Field(
        default=None,
        description="'below_threshold' (Layer 1), 'model_refused' (Layer 2), or None if answered.",
    )
    latency_ms: int | None = Field(default=None, description="Server-side time to produce this answer.")


class QueryLogOut(BaseModel):
    id: int
    question: str
    answer_json: dict
    model: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True

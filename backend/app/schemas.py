"""Pydantic request/response models shared across routers."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


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
    question: str


class Citation(BaseModel):
    doc_id: str = Field(description="The doc_id of the source document, copied exactly as given in the context.")
    issuer: str = Field(description="The issuer of the source document, copied exactly as given in the context.")
    section: str = Field(
        description="The section label of the chunk used, copied exactly from its SECTION field (e.g. '7', 'B', 'Annexure')."
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


class QueryLogOut(BaseModel):
    id: int
    question: str
    answer_json: dict
    model: str | None = None
    latency_ms: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True

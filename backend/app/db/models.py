"""Data-layer representations mirroring the Postgres schema (see db/init).

No ORM is used — queries go through asyncpg directly. These dataclasses
describe the row shapes returned from `documents`, `chunks`, and `queries`.
"""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Document:
    id: int
    doc_id: str
    title: str
    issuer: str
    doc_date: date
    status_note: str | None
    source_url: str | None
    filename: str


@dataclass
class Chunk:
    id: int
    document_id: int
    section_number: str | None
    section_title: str | None
    content: str
    embedding: list[float] | None


@dataclass
class QueryLog:
    id: int
    question: str
    answer_json: dict
    model: str | None
    latency_ms: int | None
    created_at: datetime

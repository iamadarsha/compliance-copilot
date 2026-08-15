"""Read-only endpoint listing the documents currently indexed."""

from fastapi import APIRouter

from app.db.session import get_pool
from app.schemas import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
async def list_documents():
    """Return every indexed document, oldest first.

    Exists so the frontend can render the corpus from the database rather
    than a hardcoded list. That is not a hypothetical concern: the header
    badge previously hardcoded "5 circulars indexed" and silently kept
    claiming 5 after the corpus grew to 9, because nothing tied the number
    to the data. Anything the UI says about the corpus should come from
    here.

    Ordered by date so the list reads as the regulatory timeline it is —
    the 2012 foundational circular through to the 2025 implementation
    milestones — rather than by insertion order.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, doc_id, title, issuer, doc_date, status_note, source_url, filename
            FROM documents
            ORDER BY doc_date ASC, id ASC
            """
        )
    return [DocumentOut(**dict(row)) for row in rows]

"""Endpoints for ingesting markdown source documents into the database."""

from datetime import date
from pathlib import Path

from fastapi import APIRouter

from app.db.session import get_pool
from app.rag.chunker import chunk_document, parse_frontmatter
from app.rag.embedder import embed_texts
from app.schemas import DocumentChunkCount, IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"


@router.post("", response_model=IngestResponse)
async def ingest_documents():
    """Ingest all markdown documents from backend/docs into the database.

    Parses frontmatter into `documents` rows, chunks the body, embeds each
    chunk, and stores the results in `chunks`. Idempotent: re-running clears
    any existing document/chunk rows for a given doc_id before re-inserting.
    """
    pool = await get_pool()
    per_document: list[DocumentChunkCount] = []
    total_chunks = 0

    for path in sorted(DOCS_DIR.glob("*.md")):
        raw_text = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(raw_text)

        doc_id = str(frontmatter["doc_id"])
        title = str(frontmatter["title"])
        issuer = str(frontmatter["issuer"])
        doc_date = frontmatter["date"]
        if not isinstance(doc_date, date):
            doc_date = date.fromisoformat(str(doc_date))
        status_note = frontmatter.get("status")
        source_url = frontmatter.get("source")

        chunks = chunk_document(body, doc_id)
        contents = [c["content"] for c in chunks]
        embeddings = embed_texts(contents) if contents else []

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM chunks WHERE document_id IN (SELECT id FROM documents WHERE doc_id = $1)",
                    doc_id,
                )
                await conn.execute("DELETE FROM documents WHERE doc_id = $1", doc_id)

                document_id = await conn.fetchval(
                    """
                    INSERT INTO documents (doc_id, title, issuer, doc_date, status_note, source_url, filename)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                    """,
                    doc_id,
                    title,
                    issuer,
                    doc_date,
                    status_note,
                    source_url,
                    path.name,
                )

                if chunks:
                    await conn.executemany(
                        """
                        INSERT INTO chunks (document_id, section_number, section_title, content, embedding)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        [
                            (document_id, c["section_number"], c["section_title"], c["content"], emb)
                            for c, emb in zip(chunks, embeddings)
                        ],
                    )

        per_document.append(DocumentChunkCount(doc_id=doc_id, filename=path.name, chunk_count=len(chunks)))
        total_chunks += len(chunks)

    # db/init/001_schema.sql creates the ivfflat index at schema-init time, when
    # `chunks` is still empty. The index's real correctness fix is that schema's
    # explicit lists=1 (see the comment there) — but rebuilding here too, now
    # that real data exists, is cheap insurance against ever again shipping an
    # index whose structure was decided on zero rows.
    async with pool.acquire() as conn:
        await conn.execute("REINDEX INDEX chunks_embedding_idx")
        await conn.execute("ANALYZE chunks")

    return IngestResponse(
        documents_ingested=len(per_document),
        total_chunks=total_chunks,
        chunks_per_document=per_document,
    )

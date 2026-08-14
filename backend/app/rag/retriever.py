"""Retrieves relevant chunks from pgvector via cosine similarity search."""

from app.db.session import get_pool
from app.rag.embedder import embed_query

TOP_K = 6

# Embeddings are L2-normalized by the embedder, so pgvector's cosine distance
# operator (<=>) yields similarity = 1 - distance in [0, 1] for these vectors.
_SEARCH_SQL = """
    SELECT
        c.id            AS chunk_id,
        c.section_number,
        c.section_title,
        c.content,
        d.doc_id,
        d.title         AS doc_title,
        d.issuer,
        d.doc_date,
        d.status_note,
        1 - (c.embedding <=> $1) AS similarity
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.embedding IS NOT NULL
    ORDER BY c.embedding <=> $1
    LIMIT $2
"""


async def retrieve_chunks(query: str, top_k: int = TOP_K) -> tuple[list[dict], float]:
    """Embed a query and retrieve the top-k most similar chunks.

    Args:
        query: The user's natural-language question.
        top_k: Number of chunks to retrieve.

    Returns:
        A tuple of (chunks, top_similarity). Each chunk dict carries its
        document metadata (doc_id, issuer, doc_date, status_note) alongside
        section_number/section_title/content, so the generator can reason
        about recency and supersession. top_similarity is the best cosine
        similarity found, or 0.0 when nothing was retrieved — the refusal
        gate in the query router keys off it.
    """
    embedding = embed_query(query)

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(_SEARCH_SQL, embedding, top_k)

    chunks = [dict(row) for row in rows]
    top_similarity = float(chunks[0]["similarity"]) if chunks else 0.0
    return chunks, top_similarity

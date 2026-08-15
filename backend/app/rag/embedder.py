"""Generates embeddings via a local sentence-transformers model (bge-small-en-v1.5, 384 dims)."""

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# sentence-transformers' own default internal batch size (32) processes
# nearly this whole corpus's largest per-document chunk count (12) in one
# allocation. Confirmed on the deployed instance: ingest's batch embedding
# call was enough to exceed a tight PaaS free-tier memory ceiling and
# trigger an OOM restart. Capping it costs nothing here — the whole corpus
# is a few dozen short chunks embedded once during ingest, not a
# latency-sensitive path — while meaningfully lowering the peak allocation.
_ENCODE_BATCH_SIZE = 4

# Loaded once at import time so it stays warm across requests.
_model = SentenceTransformer(_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of text chunks into 384-dim vectors.

    Args:
        texts: Chunk contents to embed.

    Returns:
        A list of 384-dimensional embedding vectors, one per input text.
    """
    embeddings = _model.encode(
        texts, batch_size=_ENCODE_BATCH_SIZE, normalize_embeddings=True, convert_to_numpy=True
    )
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single query string into a 384-dim vector.

    BGE models expect an instruction prefix on the query side only (not on
    the indexed passages) for retrieval tasks.
    """
    embedding = _model.encode(_QUERY_INSTRUCTION + text, normalize_embeddings=True, convert_to_numpy=True)
    return embedding.tolist()

"""Generates embeddings via a local sentence-transformers model (bge-small-en-v1.5, 384 dims)."""

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

# Loaded once at import time so it stays warm across requests.
_model = SentenceTransformer(_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of text chunks into 384-dim vectors.

    Args:
        texts: Chunk contents to embed.

    Returns:
        A list of 384-dimensional embedding vectors, one per input text.
    """
    embeddings = _model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single query string into a 384-dim vector.

    BGE models expect an instruction prefix on the query side only (not on
    the indexed passages) for retrieval tasks.
    """
    embedding = _model.encode(_QUERY_INSTRUCTION + text, normalize_embeddings=True, convert_to_numpy=True)
    return embedding.tolist()

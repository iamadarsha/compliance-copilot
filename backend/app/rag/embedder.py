"""Generates embeddings via ONNX Runtime (bge-small-en-v1.5, 384 dims).

Runs the model through onnxruntime + tokenizers rather than
sentence-transformers/torch. Not a preference — measured: `import torch`
alone costs ~394MB resident before a single model is touched, pushing total
peak memory past 528MB even with the smallest available embedding model.
That reliably OOM-killed this app at pure startup on Render's 512MB free
tier. The ONNX path peaks at ~234MB for the same model. Verified numerically
equivalent to the torch-based output before switching: cosine similarity
1.0 (max abs diff ~1e-7, pure floating-point noise) across a range of real
corpus and query text — nowhere close to disturbing the tuned similarity
threshold, whose narrowest observed band was 0.004.

The exported weights are `Xenova/bge-small-en-v1.5` — a widely-used ONNX
export of the same BAAI/bge-small-en-v1.5 checkpoint, baked into the image
at build time (see Dockerfile) rather than fetched at container startup, so
boot has no runtime dependency on the HF Hub being reachable.
"""

import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

_MODEL_DIR = Path(__file__).parent / "onnx_model"
_MODEL_BASE_URL = "https://huggingface.co/Xenova/bge-small-en-v1.5/resolve/main/"
_MODEL_FILES = {"model.onnx": "onnx/model.onnx", "tokenizer.json": "tokenizer.json"}
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def _ensure_model_files() -> None:
    """Download the ONNX weights if not already present.

    In production the Dockerfile bakes these into the image at build time,
    so this is a no-op there — no network dependency at container startup.
    Local dev's docker-compose bind-mounts backend/ over the image, which
    hides that baked-in copy, so this self-heals on first run instead of
    requiring a separate manual download step; the bind-mounted directory
    persists on the host afterward, so it only happens once.
    """
    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for filename, remote_path in _MODEL_FILES.items():
        dest = _MODEL_DIR / filename
        if not dest.exists():
            urllib.request.urlretrieve(_MODEL_BASE_URL + remote_path, dest)


_ensure_model_files()

# Kept small for the same reason as before, re-measured for this runtime:
# a real /ingest run against actual (long) document chunks — not short
# synthetic test strings — spiked resident memory by ~180MB mid-request and
# reliably OOM-killed the container under Render's 512MB ceiling, even
# though the ONNX session itself is flat across repeated calls in isolation.
# ONNX inference cost scales with batch_size x sequence_length^2 for
# attention, and this corpus's real chunks run close to the 512-token
# truncation ceiling — batching several of those together is what spikes.
# Ingest is a one-off, not a latency-sensitive path, so paying more wall
# time for a smaller footprint here costs nothing that matters.
_ENCODE_BATCH_SIZE = 2

# Loaded once at import time so they stay warm across requests.
_tokenizer = Tokenizer.from_file(str(_MODEL_DIR / "tokenizer.json"))
_tokenizer.enable_padding()
_tokenizer.enable_truncation(max_length=512)

# Explicit thread-pool sizing rather than relying on the OMP_NUM_THREADS env
# var alone: ONNX Runtime's default CPU execution provider uses its own
# thread pool, not necessarily OpenMP, so the env var isn't guaranteed to
# reach it. Same reasoning as the old torch setup — one thread per pool on a
# single-request-at-a-time, memory-constrained host gets nothing from
# parallelism and only adds per-thread buffer overhead.
_session_options = ort.SessionOptions()
_session_options.intra_op_num_threads = 1
_session_options.inter_op_num_threads = 1
# Both default to on, and both trade memory for speed by caching allocations
# across calls rather than returning them to the OS: the arena keeps a
# growable memory pool, and mem-pattern caches per-shape allocation plans.
# Neither cost is worth paying on a host where the failure mode isn't
# "somewhat slower" but "OOM-killed" — same tradeoff as pinning batch size
# down for the same request.
_session_options.enable_cpu_mem_arena = False
_session_options.enable_mem_pattern = False
_session = ort.InferenceSession(
    str(_MODEL_DIR / "model.onnx"), sess_options=_session_options, providers=["CPUExecutionProvider"]
)
_INPUT_NAMES = {i.name for i in _session.get_inputs()}


def _encode(texts: list[str]) -> np.ndarray:
    """Run the model over one batch: tokenize, forward pass, CLS-pool, L2-normalize.

    Replicates sentence-transformers' pipeline for this model exactly (its own
    module config reports `pooling_mode: cls`) — verified against it directly
    rather than assumed from BGE's documented convention.
    """
    all_embeddings = []
    for start in range(0, len(texts), _ENCODE_BATCH_SIZE):
        batch = texts[start : start + _ENCODE_BATCH_SIZE]
        encodings = _tokenizer.encode_batch(batch)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        feeds = {"input_ids": input_ids, "attention_mask": attention_mask}
        if "token_type_ids" in _INPUT_NAMES:
            feeds["token_type_ids"] = np.zeros_like(input_ids)

        outputs = _session.run(None, feeds)
        cls = outputs[0][:, 0]  # CLS token from last_hidden_state
        normalized = cls / np.linalg.norm(cls, axis=1, keepdims=True)
        all_embeddings.append(normalized)

    return np.concatenate(all_embeddings, axis=0)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of text chunks into 384-dim vectors.

    Args:
        texts: Chunk contents to embed.

    Returns:
        A list of 384-dimensional embedding vectors, one per input text.
    """
    return _encode(texts).tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single query string into a 384-dim vector.

    BGE models expect an instruction prefix on the query side only (not on
    the indexed passages) for retrieval tasks.
    """
    return _encode([_QUERY_INSTRUCTION + text])[0].tolist()

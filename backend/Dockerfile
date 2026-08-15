FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ONNX-exported bge-small-en-v1.5 weights, fetched once at build time and
# baked into the image — not downloaded at container startup. Two reasons:
# it removes a network dependency (and the HF Hub rate-limit warning seen at
# every prior boot) from the startup path entirely, and it keeps peak
# *runtime* memory to just the ONNX Runtime session (~234MB measured) rather
# than adding a download buffer on top during the exact window Render's free
# tier is tightest. See app/rag/embedder.py for why torch/sentence-
# transformers were dropped for this in the first place.
RUN mkdir -p app/rag/onnx_model && \
    python3 -c "\
import urllib.request; \
base = 'https://huggingface.co/Xenova/bge-small-en-v1.5/resolve/main/'; \
files = ['onnx/model.onnx', 'tokenizer.json']; \
dest = ['app/rag/onnx_model/model.onnx', 'app/rag/onnx_model/tokenizer.json']; \
[urllib.request.urlretrieve(base + f, d) for f, d in zip(files, dest)]"

COPY . .

# ONNX Runtime spins up one intra-op thread pool per available CPU core by
# default, and each thread carries its own working-memory buffers — real
# overhead on a memory-constrained instance for a single-request-at-a-time
# embedding workload that gets nothing from parallelism here.
ENV OMP_NUM_THREADS=1
ENV OMP_WAIT_POLICY=PASSIVE

EXPOSE 8000

# Shell form (not exec-form array) so $PORT expands. Render (and most PaaS
# Docker hosts) inject PORT and route to whatever the container actually
# listens on; a hardcoded port here would make the service unreachable
# despite running. Falls back to 8000 for hosts that don't set it. No
# --reload here — that's dev-only and belongs to local docker-compose's
# command override, not the image every environment inherits.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

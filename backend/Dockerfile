FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# torch's default PyPI wheel bundles the full CUDA/GPU stack on Linux (~2.9GB
# of nvidia-* packages: cublas, cudnn, cufft, nccl, ...) even though
# sentence-transformers only ever runs CPU inference here — this app never
# touches a GPU. Installing the CPU-only build first means pip already has a
# torch satisfying sentence-transformers' requirement and won't pull the GPU
# build afterward. Confirmed: cuts the image from 8.68GB to a fraction of
# that, which is very likely why a PaaS free-tier build was failing on
# disk/size limits.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Shell form (not exec-form array) so $PORT expands. Render (and most PaaS
# Docker hosts) inject PORT and route to whatever the container actually
# listens on; a hardcoded port here would make the service unreachable
# despite running. Falls back to 8000 for hosts that don't set it. No
# --reload here — that's dev-only and belongs to local docker-compose's
# command override, not the image every environment inherits.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

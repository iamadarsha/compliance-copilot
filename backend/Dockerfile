FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
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

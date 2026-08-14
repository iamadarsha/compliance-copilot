# Tech Stack

- **Frontend**: Next.js (App Router, TypeScript, Tailwind CSS), frontend-only — no server logic in Next.js API routes.
- **Backend**: Python, FastAPI.
- **Database**: PostgreSQL with the `pgvector` extension (`pgvector/pgvector:pg16` image).
- **Embeddings**: local `sentence-transformers` model, `bge-small-en-v1.5` (384 dimensions).
- **LLM**: Groq-hosted model (Groq has no embeddings endpoint, hence the local embedding model above).
- **Structured output**: `instructor`, layered over the Groq client for validated LLM responses.
- **Orchestration**: Docker Compose (`postgres`, `backend`, `frontend` services).

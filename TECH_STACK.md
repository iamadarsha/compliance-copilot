# Tech Stack

- **Frontend**: Next.js (App Router, TypeScript, Tailwind CSS), frontend-only — no server logic in Next.js API routes.
- **Backend**: Python, FastAPI.
- **Database**: PostgreSQL with the `pgvector` extension (`pgvector/pgvector:pg16` image).
- **Embeddings**: `bge-small-en-v1.5` (384 dimensions), run locally through **ONNX Runtime**
  rather than `sentence-transformers`/PyTorch. `import torch` alone costs ~394MB resident,
  which OOM-killed the container at startup on a 512MB host; the ONNX path peaks at ~234MB
  and was verified numerically equivalent before the swap. See "Embeddings" in `README.md`.
- **Generation**: Gemini (`gemini-3.5-flash-lite`) as primary, with Groq
  (`llama-3.3-70b-versatile`) as failover on provider faults only — never on a model's own
  refusal. Neither provider offers an embeddings endpoint, hence the local embedding model above.
- **Structured output**: `instructor` + Pydantic, enforcing the `ComplianceAnswer` schema
  against both providers.
- **Orchestration**: Docker Compose (`postgres`, `backend`, `frontend` services).

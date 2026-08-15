# Architecture

## Overview

Compliance Copilot is a retrieval-augmented generation (RAG) app for answering questions against a small corpus of SEBI/NSE/MCX compliance circulars.

```
frontend (Next.js, :3000)  --HTTP-->  backend (FastAPI, :8000)  --SQL-->  postgres + pgvector (:5432)
```

The Next.js frontend holds no backend logic — every request that needs data or an LLM call goes through the FastAPI service. This keeps ingestion, retrieval, and generation logic in one place, testable independently of the UI.

## Backend layout

- `app/routers/ingest.py` — ingests the markdown source documents in `backend/docs/`.
- `app/routers/query.py` — answers a question: retrieval, the two-layer refusal gate, then generation.
- `app/routers/documents.py` — lists the indexed corpus, so the UI renders it from the database rather than a hardcoded list.
- `app/rag/chunker.py` — splits a document's markdown body into section-aware chunks.
- `app/rag/embedder.py` — embeds chunks/queries locally via ONNX Runtime (`bge-small-en-v1.5`).
- `app/rag/retriever.py` — cosine-similarity search over `chunks.embedding` via pgvector.
- `app/rag/generator.py` — produces a cited answer, Gemini-primary with Groq failover, and applies the citation-consistency check.
- `app/rag/meta.py` — answers questions about the assistant itself ("what can you do?") deterministically from the `documents` table, only for questions retrieval was already going to refuse.
- `app/db/` — connection/session management and row-shape definitions for the schema below.

## Query path

1. Retrieve the top-6 chunks by cosine similarity.
2. **Layer 1** — if the top score is below the tuned threshold (0.69), skip the model
   entirely. Before refusing, check whether the question is *about the assistant* and, if
   so, answer it from the `documents` table.
3. **Layer 2** — otherwise generate, and let the model refuse if the retrieved text does
   not actually support an answer.
4. Post-generation, an answer claiming `refused=false` without a `primary` citation is
   downgraded to a cautious refusal rather than presented as confident.

## Data model

- `documents` — one row per source circular, mapping directly onto the YAML frontmatter (`doc_id`, `title`, `issuer`, `date`, `status`, `source`) of each markdown file in `backend/docs/`.
- `chunks` — section-level chunks of a document's body, each with a 384-dim embedding (`vector(384)`), indexed with an IVFFlat cosine-distance index for retrieval.
- `queries` — a log of each question asked, the full answer (including citations) as JSON, the model used, and latency, for evaluation and debugging.

## Evaluation

`backend/eval/` holds a test set (`test_set.json`) of 10 question/expected-answer pairs — 6
answerable, 4 deliberately not — and a runner (`run_eval.py`) that exercises the `/query`
endpoint and reports retrieval hit rate, citation accuracy, refusal accuracy split by which
layer fired, and a similarity distribution used to tune the threshold. Run it with:

```bash
docker compose exec backend python -m eval.run_eval
```

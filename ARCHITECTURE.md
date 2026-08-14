# Architecture

## Overview

Compliance Copilot is a retrieval-augmented generation (RAG) app for answering questions against a small corpus of SEBI/NSE/MCX compliance circulars.

```
frontend (Next.js, :3000)  --HTTP-->  backend (FastAPI, :8000)  --SQL-->  postgres + pgvector (:5432)
```

The Next.js frontend holds no backend logic — every request that needs data or an LLM call goes through the FastAPI service. This keeps ingestion, retrieval, and generation logic in one place, testable independently of the UI.

## Backend layout

- `app/routers/ingest.py` — ingests the markdown source documents in `backend/docs/`.
- `app/routers/query.py` — answers a question via retrieval + generation.
- `app/rag/chunker.py` — splits a document's markdown body into section-aware chunks.
- `app/rag/embedder.py` — embeds chunks/queries with a local sentence-transformers model.
- `app/rag/retriever.py` — cosine-similarity search over `chunks.embedding` via pgvector.
- `app/rag/generator.py` — calls the Groq-hosted LLM to produce a cited answer from retrieved chunks.
- `app/db/` — connection/session management and row-shape definitions for the schema below.

All of the above are currently stubs (function signatures + docstrings only); implementation comes in later phases.

## Data model

- `documents` — one row per source circular, mapping directly onto the YAML frontmatter (`doc_id`, `title`, `issuer`, `date`, `status`, `source`) of each markdown file in `backend/docs/`.
- `chunks` — section-level chunks of a document's body, each with a 384-dim embedding (`vector(384)`), indexed with an IVFFlat cosine-distance index for retrieval.
- `queries` — a log of each question asked, the full answer (including citations) as JSON, the model used, and latency, for evaluation and debugging.

## Evaluation

`backend/eval/` holds a test set (`test_set.json`) of question/expected-answer pairs and a runner (`run_eval.py`) that will exercise the `/query` endpoint once retrieval and generation are implemented.

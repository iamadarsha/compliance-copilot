# Design Decisions

- **All backend logic lives in FastAPI, not Next.js API routes.** Deliberate separation so the RAG pipeline (ingestion, chunking, embedding, retrieval, generation) is independently testable and language-appropriate (Python has the ML tooling), while the frontend stays a thin client.
- **pgvector over a dedicated vector DB.** The corpus is 5 documents — Postgres with `pgvector` avoids running a second stateful service for a workload this small, and keeps document metadata and embeddings in one place with normal SQL joins.
- **Local embeddings (`bge-small-en-v1.5`, 384-dim), Groq for generation.** Groq does not offer an embeddings endpoint, so embedding must happen locally; `bge-small-en-v1.5` is a strong, small, CPU-friendly model for a corpus this size.
- **`documents` schema mirrors source frontmatter directly.** Each markdown source file's YAML frontmatter (`doc_id`, `title`, `issuer`, `date`, `status`, `source`, `retrieved`) maps one-to-one onto `documents` columns, so ingestion is a straight parse-and-insert with no reshaping.
- **`status_note` is free text, not an enum.** Circular status ("superseded in part — see doc 03") needs to reference other documents and carry nuance that a fixed enum can't express with only 5 source documents.
- **`queries` logs the full answer as `jsonb`.** Keeping the answer (including citations) as a single JSON blob, alongside `model` and `latency_ms`, makes the table double as an eval/debugging log without needing a separate citations table.
- **Routers and RAG modules are stubbed in this phase.** Folder structure, schema, and scaffolding are set up first; ingestion, retrieval, and generation logic are implemented in later phases, one at a time.

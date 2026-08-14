-- Compliance Copilot schema: run automatically by the pgvector/pgvector
-- Postgres image on first container boot (files in /docker-entrypoint-initdb.d).

create extension if not exists vector;

create table documents (
  id serial primary key,
  doc_id text not null,          -- e.g. 'SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013'
  title text not null,
  issuer text not null,          -- 'SEBI' | 'NSE' | 'MCX'
  doc_date date not null,
  status_note text,              -- free text, e.g. 'superseded in part — see doc 03'
  source_url text,
  filename text not null
);

create table chunks (
  id serial primary key,
  document_id integer references documents(id),
  section_number text,           -- e.g. '4' or 'Annexure'
  section_title text,
  content text not null,
  embedding vector(384)
);

-- lists=1 is deliberate, not a default left unset. ivfflat is an approximate
-- index whose cluster count is normally sized to the row count; with a corpus
-- this small (tens of chunks), pgvector's own defaults produce multiple
-- near-empty clusters, and the default probes=1 then checks only one of them
-- per query — silently returning 0 or partial results for most queries even
-- though the data and embeddings are correct. lists=1 makes the single list
-- contain every row, so a search always scans all of it: correctness over an
-- approximate-search speedup this corpus is far too small to need. Revisit
-- if the corpus grows into the thousands of chunks.
create index on chunks using ivfflat (embedding vector_cosine_ops) with (lists = 1);

create table queries (
  id serial primary key,
  question text not null,
  answer_json jsonb not null,
  model text,
  latency_ms integer,
  created_at timestamptz default now()
);

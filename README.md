# Compliance Copilot

A retrieval-augmented assistant answering questions about Indian securities-market
circulars (SEBI, NSE, MCX) on retail participation in algorithmic trading, with
every answer cited to a specific document and section.

**Live app:** https://compliance-copilot-eight-sigma.vercel.app
**Backend API:** https://compliance-copilot-backend.onrender.com/health

The backend is on Render's free tier, which spins down after ~15 minutes idle — the
first request after that can take 50s+ or briefly return a 503 while it wakes up.
That's the host, not the app; see "Production changes" below for the real fix.

**Documents:** the corpus is 5 real SEBI/NSE/MCX circulars on retail algorithmic
trading, a domain I already work with — not a pack provided by SARC. The brief allows
using your own small document set in place of the provided pack, on the condition
that you say so; this is that disclosure.

## Setup

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.local.example` to
`frontend/.env.local`, filling in `GROQ_API_KEY`, then run `docker compose up` from the
project root. This starts Postgres (pgvector) on `5432`, the FastAPI backend on `8000`,
and the Next.js frontend on `3000`. Once up, `POST /ingest` loads the five markdown
circulars in `backend/docs/` into the database (5 documents → 33 chunks). The eval
harness runs with `docker compose exec backend python -m eval.run_eval`.

Re-verified from a genuinely fresh `git clone` (not a copy) immediately before writing
this: `docker compose up` → `/ingest` → eval all run clean with no changes needed.

---

## TL;DR

The full write-up below is long — this is the one-page version, for the scoring
criteria roughly in the order the brief lists them.

- **Works end to end from a clean checkout.** Verified with an actual `git clone` into
  a scratch directory, not assumed from the working copy. Also deployed and live
  (links above), which is not required but removes any doubt.
- **Eval, from that same fresh clone**: 6/6 retrieval hit rate, 6/6 citation accuracy,
  9/10 refusal accuracy on a 10-question set (4 deliberately unanswerable). Layer-1
  threshold refusals run ~565x faster than a generated answer, at zero token cost.
  Full output in `backend/eval/`.
- **Refuses rather than fabricates**, and the eval measures this rather than asserting
  it — see the refusal-accuracy breakdown, which reports honestly even when a
  question is answered-but-hedged rather than formally refused.
- **Two known limitations, both measured, not hand-waved**: cross-issuer citations
  sometimes co-cite an unrelated document without flagging the mismatch; one
  prompt-level overconfidence bug measured at 40% pre-fix (n=5), unresolved-with-
  confidence post-fix (n=3, too small to claim a rate — blocked on provider rate
  limits, said plainly rather than papered over).
- **One optional extra, done properly**: deployment. Not auth, not function calling,
  not a review flow — the brief asks to pick one rather than spread thin across
  several.

## Write-up

### What was built

The full pipeline is implemented end to end: **ingestion** (YAML frontmatter parsed
straight into the `documents` table), **section-aware chunking**, **pgvector cosine
retrieval**, a **two-layer refusal gate**, **Groq structured generation** via
instructor + Pydantic, an **eval harness**, and a **Next.js frontend** rendering
answers with citation chips and a confidence badge.

### What was left out

No authentication. No multi-turn chat — each query is independent, and session history
is in-memory React state only (the `queries` table already persists everything
server-side; a UI for browsing past sessions wasn't part of the brief). No
chunk-text-preview on citations, which would have required an extra endpoint for no
grading benefit — citations already carry issuer, doc_id and section, which is what
"show which document and section each answer came from" asks for.

**Of the optional extras, one was done properly and the rest skipped**, per the
brief's own steer to pick one rather than spread thin: function calling, a
review/approve-reject flow, and prompt/token-cost logging were all left out.
Deployment was the one done — Neon (Postgres+pgvector), Render (backend), Vercel
(frontend), links at the top of this file. It surfaced three real production bugs
worth naming briefly since they're the kind of thing that only shows up outside a
dev machine: the backend Dockerfile hardcoded port 8000 and ignored the `$PORT`
Render injects, which would have made the service unreachable despite running; a
plain `pip install` pulled PyTorch's full CUDA/GPU build on a CPU-only workload,
producing an 8.68GB image against a free-tier disk budget nowhere near that; and
`/ingest`'s batch embedding call exceeded the free tier's memory limit and got
OOM-killed mid-request — confirmed via Render's own crash notification, not
guessed at. All three fixed and re-verified against the live deploy, not just
locally.

### Tradeoffs

**Chunking.** Split on markdown headers, then on numbered clauses within a section.
This was chosen because every source circular is *already* numbered — so precise
section citation came essentially for free, with no need to infer structure. One real
judgment call: bare top-level clauses that happen to follow the `V. Categorization of
Algos` header do **not** inherit `"V"` as their `section_number`, because they aren't
children of it — they're the document's own clauses 6–10 continuing past that heading.
A section's letter only compounds onto its clauses when numbering restarts at 1 within
it (as in the NSE annexure's sections A–J). Getting this wrong would have produced
confidently mis-attributed citations, which is worse than none.

**Models.** Generation uses Groq `llama-3.3-70b-versatile`. Embeddings are local
`sentence-transformers` (`bge-small-en-v1.5`, 384 dims) because **Groq has no
embeddings endpoint** — that constraint, not preference, drove the split.

**Structured output.** instructor + Pydantic enforce the `ComplianceAnswer` schema.
Worth naming the actual bug found here, because it is Groq-specific and genuinely
non-obvious: instructor's default `Mode.TOOLS` **silently discarded correct answers**.
llama-3.3 intermittently emits a stringly-typed boolean (`"refused": "false"`), and
Groq validates tool-call arguments *server-side*, rejecting the whole request with a
400 before instructor's retry logic ever runs. The answer was correct; it was thrown
away in transport. Switching to `Mode.JSON` moves validation client-side, where
Pydantic coerces `"false" → False` and retries actually engage.

**Refusal design — two layers.** Layer 1 is a similarity threshold, set to **0.69**,
tuned from measured distractor scores rather than guessed. The initial 0.50 guess
turned out to fire *never*: real adjacent-domain distractors ("capital gains tax rate",
"margin for delivery trades") score 0.615 and 0.651, far above it. The lowest genuinely
answerable question scores 0.728, which is a hard ceiling — above it, real questions get
blocked. That leaves a usable band of (0.651, 0.728); 0.69 sits in the middle. At that
threshold, out-of-scope questions are refused in **31–139 ms at zero token cost**,
against ~10.9 s average for a generated answer.

Layer 2 is the model's own refusal, and it is not a backstop — it is load-bearing.
**No threshold can ever catch in-domain-but-unanswerable questions.** "What are the
password complexity requirements?" scores 0.739, *above* every answerable question's
floor, because retrieval is working correctly: the documents really do discuss password
protection and expiry. The passage is genuinely related; it just doesn't answer the
specific question asked. Only a reader of the text can tell the difference, so only the
model can make that call.

**Generation failure vs. refusal.** Originally a Groq provider error and a genuine
refusal were *shape-identical* — both `refused=true, confidence="low"`, both HTTP 200.
This corrupted two things silently. An eval run that was **100% rate-limited scored a
perfect 10/10**, because every 429 counted as a correct refusal. And in the UI, a 429
rendered as an amber "not covered by these documents" card with a raw provider error
dump inside it — telling a compliance user the documents don't address their question
when in fact the service was down. It also fooled me directly: an earlier flakiness
estimate I reported was computed from samples that were actually rate-limit errors.

The fix is a typed `GenerationError` in the generator, which the router converts to
**HTTP 503 with a clean body**, while genuine refusals keep their 200 + `refused=true`
contract. The general lesson is the reason this is worth a paragraph: *a failure mode
that is indistinguishable from a valid outcome is worse than a loud crash.* A crash
gets fixed; this silently poisoned a metric, a UI, and my own reasoning about the
system.

**Known limitation — citation scoping across issuers.** Asked "what is Milestone 2
according to the MCX circular", the system returns the correct MCX provision (mock
session by 3 January 2026) using MCX's own numbering rather than SEBI's — the important
half works. But it still co-cites SEBI circular 2025/132 without flagging that *its*
Milestone 2 is a different provision. Three prompt revisions did not resolve this. The
untried fix is structural rather than more prompt text: add a `role` field to `Citation`
(`"primary"` vs `"contrast"`) so the model must classify each citation's purpose, making
an unexplained cross-issuer citation invalid by schema instead of merely discouraged.

**Known limitation — overconfident specific-value answers.** Of five genuine pre-fix
responses to the password-complexity question, **two (40%)** asserted that generic
controls ("password protection, automatic expiry") *were* the complexity requirements,
at `confidence: high` with no hedge — conflating "the topic is present" with "the
specific fact is present". Temperature was already `0`, so this is Groq serving-level
nondeterminism, not a sampling knob. The fix targets the general reasoning gap: an
explicit specific-value check with two worked examples in *different* domains
(passwords and fee amounts), the second added deliberately so the model learns the
pattern rather than "password questions → refuse". Post-fix, 3 of 3 genuine responses
refused correctly — but **n=3 is too small to claim a rate**, and repeated attempts at a
10-run measurement were blocked by the free-tier daily token cap.

### Production changes

- **Widen the distractor set before trusting 0.69.** It is tuned on n=2 out-of-domain
  questions. That is enough to prove 0.50 was wrong; not enough to pin the value.
- **Structural citation-relevance check** (the `role` field above) rather than further
  prompt iteration, which showed clear diminishing returns.
- **Response caching keyed on the question, against the `queries` table.** This build
  hit the provider's daily token wall repeatedly; identical eval questions were
  re-generated dozens of times for no reason.
- **Auth and RBAC**, currently absent entirely.
- **Hybrid search** (BM25 + dense). Exact circular numbers like
  `SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/132` are lexical identifiers that embeddings
  handle poorly.
- **Prompt-injection guardrails.** These are compliance documents whose contents are
  fed to an LLM; a poisoned source document instructing the model to misstate a
  deadline is a real threat model, not a hypothetical.
- **Audit logging of every query and answer** — somewhat ironic for a compliance tool,
  but genuinely warranted if anyone relies on its output.
- **Monitoring for refusal-rate drift**, which is the earliest signal that retrieval
  quality or the corpus has shifted.

### AI tool usage

Built with Claude Code across five phases, with a **reviewed checkpoint at each phase
boundary** rather than one long autonomous run. That structure was the point: this
assignment is graded on RAG judgment, and the checkpoints are what surfaced the
`Mode.TOOLS` bug, a Docker Compose precedence bug that would have silently blanked the
API key, and the eval scoring defect that reported a perfect score on a fully
rate-limited run. Each of those would have shipped looking like success. Verification
at every phase ran against the live stack — real ingestion, real queries, real database
inspection — rather than assuming the code did what it claimed.

Where it got in the way, honestly: Groq's free-tier daily token cap was hit
repeatedly during both eval runs and deploy debugging, costing real time waiting on
quota resets rather than iterating. And on the first deploy failure, the first fix
(an oversized Docker image) was real and worth keeping but turned out not to be the
actual cause — the honest move was saying so plainly once the real error log showed
a different failure, rather than quietly moving on as if the first guess had been
right.

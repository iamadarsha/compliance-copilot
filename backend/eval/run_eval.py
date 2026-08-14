"""Runs backend/eval/test_set.json questions against /query and scores the answers.

Run from the backend container (where DATABASE_URL and the API are reachable):

    docker compose exec backend python -m eval.run_eval

Read-only with respect to the RAG pipeline: it calls the live /query endpoint and
reads back the `queries` row each call creates, plus re-runs retrieval to inspect
what was actually in top-k. It never modifies retriever/generator/query logic.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import asyncpg
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.retriever import TOP_K, retrieve_chunks  # noqa: E402
from app.routers.query import SIMILARITY_THRESHOLD  # noqa: E402

API_URL = os.environ.get("EVAL_API_URL", "http://localhost:8000")
DATABASE_URL = os.environ["DATABASE_URL"]
TEST_SET = Path(__file__).parent / "test_set.json"
RESULTS_OUT = Path(__file__).parent / "last_run.json"

# The test set names documents by short human labels; the DB stores full doc_ids.
# Each alias maps to a substring that must match exactly one document — validated
# at startup so a doc_id change fails loudly instead of silently scoring 0.
DOC_ALIASES = {
    "SEBI CIR/2025/013": "/CIR/2025/0000013",
    "SEBI CIR/2025/046": "/CIR/2025/46",
    "SEBI CIR/2025/132": "/CIR/2025/132",
    "NSE 471/2025": "471/2025",
    "MCX Reminder": "MCX Circular (Reminder)",
}

# Phrases that mark an answer as explicitly disclaiming a gap rather than
# fabricating over it. Used to distinguish "correctly scoped, not formally
# refused" from "hallucinated" on expected_answerable=false questions.
_GAP_PHRASES = (
    "not included",
    "not specified",
    "does not specify",
    "do not specify",
    "not detailed",
    "not available",
    "not provided",
    "not part of",
    "isn't included",
    "is not in",
    "not mentioned",
    "no information",
)


def _norm(text: str) -> str:
    """Normalize for substring comparison.

    Lowercases, collapses whitespace, and strips leading zeros from 1-2 digit
    numbers so the test set's "April 1, 2026" matches the circulars' literal
    "April 01, 2026". Without this the eval reports false failures on date
    formatting rather than on retrieval or grounding.
    """
    text = text.lower()
    text = re.sub(r"\b0(\d)\b", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains(haystack: str, needle: str) -> bool:
    return _norm(needle) in _norm(haystack)


def _chunk_label(section_number: str | None, section_title: str | None) -> str:
    """Rebuild the SECTION label the generator shows the model.

    Mirrors the formatting in app/rag/generator.py:_format_context so citations
    can be resolved back to the chunk they came from. Kept as a local copy
    rather than importing a private helper; if that formatting changes, the
    "cite unresolved" column here is what will surface the drift.
    """
    label = section_number or "(unnumbered)"
    if section_title:
        label = f"{label} — {section_title}"
    return label


def _doc_id_matches(cited: str, actual: str) -> bool:
    """Match a model-written doc_id against a stored one, tolerating truncation.

    The model is told to copy doc_id verbatim but sometimes shortens it (e.g.
    "NSE/INVG/67858" for "NSE/INVG/67858 (Circular Ref. No. 471/2025)"). Exact
    matching would score that as a grounding failure when the source is in fact
    correct, so matching is lenient here and verbatim-ness is tracked separately
    as its own citation-fidelity metric.
    """
    c, a = _norm(cited), _norm(actual)
    return c == a or a.startswith(c) or c.startswith(a)


def _resolve_citation(citation: dict, doc_chunks: list[dict]) -> dict | None:
    """Map a model-written citation back to the stored chunk it refers to."""
    section = (citation.get("section") or "").strip()
    cited_doc = citation.get("doc_id", "")
    candidates = [c for c in doc_chunks if _doc_id_matches(cited_doc, c["doc_id"])]
    # A truncated id that matches several documents is genuinely ambiguous.
    if len({c["doc_id"] for c in candidates}) > 1:
        return None
    if not candidates:
        return None

    # 1: full label match, 2: section-number match, 3: title match.
    for c in candidates:
        if _norm(section) == _norm(_chunk_label(c["section_number"], c["section_title"])):
            return c
    head = re.split(r"\s+[—-]\s+", section)[0].strip()
    for c in candidates:
        stored = c["section_number"] or "(unnumbered)"
        if head and _norm(head) == _norm(stored):
            return c
    for c in candidates:
        if c["section_title"] and _norm(c["section_title"]) in _norm(section):
            return c
    return None


async def _load_documents(conn) -> list[dict]:
    rows = await conn.fetch("SELECT id, doc_id FROM documents ORDER BY id")
    return [dict(r) for r in rows]


def _resolve_alias(alias: str, documents: list[dict]) -> str:
    needle = DOC_ALIASES.get(alias)
    if needle is None:
        raise SystemExit(f"Test set references unknown expected_doc alias {alias!r}.")
    matches = [d["doc_id"] for d in documents if needle in d["doc_id"]]
    if len(matches) != 1:
        raise SystemExit(
            f"Alias {alias!r} (pattern {needle!r}) matched {len(matches)} documents; expected exactly 1."
        )
    return matches[0]


async def _fetch_query_row(conn, question: str, usable_only: bool = False) -> dict | None:
    """Fetch the most recent stored answer for a question.

    usable_only skips rows whose generation errored (e.g. a provider rate limit),
    so offline re-scoring works against real model output rather than error text.
    """
    clause = (
        "AND answer_json->>'refusal_reason' IS DISTINCT FROM 'generation_error'"
        if usable_only
        else ""
    )
    row = await conn.fetchrow(
        f"""
        SELECT id, answer_json, model, latency_ms, created_at
        FROM queries
        WHERE question = $1 {clause}
        ORDER BY id DESC
        LIMIT 1
        """,
        question,
    )
    if row is None:
        return None
    record = dict(row)
    record["answer_json"] = json.loads(record["answer_json"])
    return record


async def run_case(
    client: httpx.AsyncClient, conn, case: dict, documents: list[dict], offline: bool = False
) -> dict:
    question = case["question"]

    if offline:
        # Re-score the most recent real answer already in `queries` instead of
        # calling the API. Costs no tokens; used when the provider is rate-limited
        # or when only the scoring logic changed.
        row = await _fetch_query_row(conn, question, usable_only=True)
        if row is None:
            raise SystemExit(
                f"Offline mode: no usable stored answer for {case['id']!r}. Run online at least once."
            )
        answer = {k: row["answer_json"][k] for k in ("answer", "citations", "confidence", "refused")}
    else:
        response = await client.post(f"{API_URL}/query", json={"question": question}, timeout=180.0)
        if response.status_code == 503:
            # Generation outage. The server already logged it as
            # generation_error, which drives result["valid"] = False below, so
            # the run is discarded rather than scored. Placeholders here must
            # never look like a real verdict.
            answer = {"answer": "", "citations": [], "confidence": "low", "refused": False}
        else:
            response.raise_for_status()
            answer = response.json()
        row = await _fetch_query_row(conn, question)

    stored = row["answer_json"] if row else {}
    refusal_reason = stored.get("refusal_reason")
    latency_ms = row["latency_ms"] if row else None
    top_similarity = stored.get("top_similarity")

    # Re-run retrieval to see the full top-k (the API returns citations only).
    retrieved, retrieved_top = await retrieve_chunks(question)
    if top_similarity is None:
        top_similarity = round(retrieved_top, 4)

    result = {
        "id": case["id"],
        "question": question,
        "expected_answerable": case["expected_answerable"],
        "expected_doc": case.get("expected_doc"),
        "expected_answer_contains": case.get("expected_answer_contains"),
        "notes": case.get("notes"),
        "answer": answer["answer"],
        "citations": answer["citations"],
        "confidence": answer["confidence"],
        "refused": answer["refused"],
        "refusal_reason": refusal_reason,
        "latency_ms": latency_ms,
        "top_similarity": float(top_similarity),
        "similarity_agreement": abs(float(top_similarity) - retrieved_top) < 1e-3,
        "retrieved_docs": sorted({c["doc_id"] for c in retrieved}),
        "cited_docs": sorted({c["doc_id"] for c in answer["citations"]}),
        "scored_from": "stored" if offline else "live",
        "answered_at": str(row["created_at"]) if row and row.get("created_at") else None,
    }

    # --- retrieval hit rate (answerable only) ---
    if case["expected_answerable"]:
        expected_doc_id = _resolve_alias(case["expected_doc"], documents)
        result["expected_doc_id"] = expected_doc_id
        result["retrieval_hit"] = any(c["doc_id"] == expected_doc_id for c in retrieved)
    else:
        result["expected_doc_id"] = None
        result["retrieval_hit"] = None

    # --- answer-content and citation-grounding checks (answerable only) ---
    expected_text = case.get("expected_answer_contains")
    if case["expected_answerable"] and expected_text:
        result["answer_contains"] = _contains(answer["answer"], expected_text)

        doc_chunks = [dict(c) for c in retrieved]
        known_doc_ids = {d["doc_id"] for d in documents}
        resolved, unresolved, non_verbatim = [], 0, []
        for citation in answer["citations"]:
            chunk = _resolve_citation(citation, doc_chunks)
            if citation.get("doc_id") not in known_doc_ids:
                non_verbatim.append(citation.get("doc_id"))
            if chunk is None:
                unresolved += 1
            else:
                resolved.append(chunk)
        result["citations_unresolved"] = unresolved
        result["citations_non_verbatim"] = non_verbatim
        result["citation_grounded"] = any(_contains(c["content"], expected_text) for c in resolved)
        result["cited_expected_doc"] = any(
            c["doc_id"] == result["expected_doc_id"] for c in resolved
        )
        result["extra_cited_docs"] = [
            d for d in result["cited_docs"] if d != result["expected_doc_id"]
        ]
    else:
        result["answer_contains"] = None
        result["citation_grounded"] = None
        result["cited_expected_doc"] = None
        result["citations_unresolved"] = None
        result["citations_non_verbatim"] = [
            c.get("doc_id") for c in answer["citations"]
            if c.get("doc_id") not in {d["doc_id"] for d in documents}
        ]
        result["extra_cited_docs"] = []

    # --- refusal decision ---
    # A generation error (e.g. provider rate limit) surfaces as refused=True /
    # confidence=low, which is indistinguishable from a genuine refusal by shape
    # alone. Mark it invalid so it can never be scored as a pass — otherwise a
    # rate-limited run reports a perfect refusal rate.
    result["valid"] = refusal_reason != "generation_error"
    result["decision_correct"] = (
        answer["refused"] == (not case["expected_answerable"]) if result["valid"] else False
    )
    result["gap_flagged"] = any(p in answer["answer"].lower() for p in _GAP_PHRASES)
    return result


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "  n/a"
    return f"{100 * numerator / denominator:5.1f}%"


def _mark(value) -> str:
    if value is None:
        return " - "
    return " ok" if value else "FAIL"


def print_report(results: list[dict]) -> None:
    answerable = [r for r in results if r["expected_answerable"]]
    unanswerable = [r for r in results if not r["expected_answerable"]]
    line = "=" * 108

    errored = [r for r in results if not r.get("valid", True)]
    if errored:
        print(f"\n{'!' * 108}")
        print(f"!! INVALID RUN: {len(errored)}/{len(results)} question(s) failed to generate "
              f"(provider error, e.g. rate limit).")
        print("!! Errored questions surface as refused=True/confidence=low, which LOOKS like a")
        print("!! refusal but is not one. Scores below are NOT a measurement of model behaviour.")
        print(f"!! Affected: {', '.join(r['id'] for r in errored)}")
        print(f"{'!' * 108}")

    print(f"\n{line}\nPER-QUESTION RESULTS\n{line}")
    header = (
        f"{'id':<4} {'answerable':<11} {'sim':>6} {'refused':<8} {'layer':<11} "
        f"{'conf':<7} {'retr':<5} {'ans':<5} {'cite':<5} {'gapflag':<8} {'ms':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        layer = {
            "below_threshold": "L1 thresh",
            "model_refused": "L2 model",
            "generation_error": "ERROR",
        }.get(r["refusal_reason"], "-")
        print(
            f"{r['id']:<4} {str(r['expected_answerable']):<11} {r['top_similarity']:>6.3f} "
            f"{str(r['refused']):<8} {layer:<11} {r['confidence']:<7} "
            f"{_mark(r['retrieval_hit']):<5} {_mark(r['answer_contains']):<5} "
            f"{_mark(r['citation_grounded']):<5} {str(r['gap_flagged']):<8} "
            f"{r['latency_ms'] if r['latency_ms'] is not None else -1:>7}"
        )

    # ---- retrieval / citation ----
    print(f"\n{line}\nRETRIEVAL & CITATION (answerable questions only, top_k={TOP_K})\n{line}")
    hits = sum(1 for r in answerable if r["retrieval_hit"])
    ans_ok = sum(1 for r in answerable if r["answer_contains"])
    cite_ok = sum(1 for r in answerable if r["citation_grounded"])
    cited_doc_ok = sum(1 for r in answerable if r["cited_expected_doc"])
    unresolved = sum(r["citations_unresolved"] or 0 for r in answerable)
    n = len(answerable)
    print(f"Retrieval hit rate (expected_doc in top-{TOP_K}) : {hits}/{n}  {_pct(hits, n)}")
    print(f"Answer contains expected string              : {ans_ok}/{n}  {_pct(ans_ok, n)}")
    print(f"Citation accuracy (cited chunk supports it)  : {cite_ok}/{n}  {_pct(cite_ok, n)}")
    print(f"Cited the expected document at all           : {cited_doc_ok}/{n}  {_pct(cited_doc_ok, n)}")
    print(f"Citations that could not be resolved to a chunk: {unresolved}")

    non_verbatim = [(r["id"], d) for r in results for d in (r.get("citations_non_verbatim") or [])]
    if non_verbatim:
        print(f"\nCitation fidelity: {len(non_verbatim)} citation(s) did not copy doc_id verbatim")
        print("(source still resolves correctly; this is an exactness problem, not a grounding one)")
        for qid, d in non_verbatim:
            print(f"  {qid}: cited {d!r}")

    extras = [r for r in answerable if r["extra_cited_docs"]]
    if extras:
        print("\nCo-citations beyond the expected document (informational, not scored):")
        for r in extras:
            for d in r["extra_cited_docs"]:
                print(f"  {r['id']}: also cited {d[:72]}")

    # ---- refusal ----
    print(f"\n{line}\nREFUSAL ACCURACY (by layer)\n{line}")
    correct = sum(1 for r in results if r["decision_correct"])
    l1 = [r for r in results if r["refusal_reason"] == "below_threshold"]
    l2 = [r for r in results if r["refusal_reason"] == "model_refused"]
    print(f"Correct refuse/answer decision : {correct}/{len(results)}  {_pct(correct, len(results))}")
    print(f"  on answerable questions      : "
          f"{sum(1 for r in answerable if r['decision_correct'])}/{len(answerable)}")
    print(f"  on unanswerable questions    : "
          f"{sum(1 for r in unanswerable if r['decision_correct'])}/{len(unanswerable)}")
    print()
    print(f"{'':<32}{'Layer 1 (threshold)':<22}{'Layer 2 (model)':<20}")
    print(f"{'refusals fired':<32}{len(l1):<22}{len(l2):<20}")
    print(f"{'  ids':<32}{','.join(r['id'] for r in l1) or '-':<22}{','.join(r['id'] for r in l2) or '-':<20}")

    missed = [r for r in unanswerable if not r["decision_correct"]]
    if missed:
        print("\nUnanswerable questions that were NOT formally refused:")
        for r in missed:
            state = "explicitly flagged the gap" if r["gap_flagged"] else "NO GAP DISCLAIMER — possible fabrication"
            print(f"  {r['id']}: refused=False, confidence={r['confidence']}, {state}")

    # ---- latency ----
    print(f"\n{line}\nLATENCY\n{line}")
    thresh_lat = [r["latency_ms"] for r in l1 if r["latency_ms"] is not None]
    gen_lat = [
        r["latency_ms"] for r in results
        if r["refusal_reason"] != "below_threshold" and r["latency_ms"] is not None
    ]
    print(f"{'path':<34}{'n':>4}{'avg ms':>10}{'max ms':>10}")
    print("-" * 58)
    if thresh_lat:
        print(f"{'Layer 1 threshold-refused (no LLM)':<34}{len(thresh_lat):>4}"
              f"{sum(thresh_lat) / len(thresh_lat):>10.0f}{max(thresh_lat):>10}")
    if gen_lat:
        print(f"{'Generated (Groq call)':<34}{len(gen_lat):>4}"
              f"{sum(gen_lat) / len(gen_lat):>10.0f}{max(gen_lat):>10}")
    if thresh_lat and gen_lat:
        avg_t = sum(thresh_lat) / len(thresh_lat)
        avg_g = sum(gen_lat) / len(gen_lat)
        print(f"\n  >> Layer 1 short-circuit is {avg_g / avg_t:.0f}x faster on average "
              f"({avg_t:.0f} ms vs {avg_g:.0f} ms).")
        print(f"  >> It answers off-scope questions in ~{avg_t:.0f} ms at zero token cost.")

    # ---- threshold distribution ----
    print(f"\n{line}\nSIMILARITY DISTRIBUTION (threshold = {SIMILARITY_THRESHOLD:.2f})\n{line}")
    print(f"{'id':<5}{'expected_answerable':<21}{'similarity':>11}   {'vs threshold':<14}")
    print("-" * 56)
    for r in sorted(results, key=lambda x: -x["top_similarity"]):
        side = "above" if r["top_similarity"] >= SIMILARITY_THRESHOLD else "BELOW (refused)"
        print(f"{r['id']:<5}{str(r['expected_answerable']):<21}{r['top_similarity']:>11.4f}   {side:<14}")

    if answerable and unanswerable:
        lo = min(answerable, key=lambda r: r["top_similarity"])
        ceiling = lo["top_similarity"]

        # The only hard constraint on Layer 1 is that it must never block a
        # question the documents CAN answer. That puts a hard ceiling on the
        # threshold at the lowest answerable score. Everything below that
        # ceiling is free to catch.
        catchable = sorted(
            [r for r in unanswerable if r["top_similarity"] < ceiling],
            key=lambda r: -r["top_similarity"],
        )
        uncatchable = sorted(
            [r for r in unanswerable if r["top_similarity"] >= ceiling],
            key=lambda r: -r["top_similarity"],
        )

        print(f"\nHard ceiling on the threshold : {ceiling:.4f}  (lowest answerable score, {lo['id']})")
        print(f"                                 any higher value starts blocking real questions.")
        print(f"Currently configured           : {SIMILARITY_THRESHOLD:.4f}")

        if catchable:
            best = catchable[0]["top_similarity"]
            lower, upper = best, ceiling
            suggested = round((lower + upper) / 2, 2)
            catchable_desc = ", ".join(
                "{}={:.3f}".format(r["id"], r["top_similarity"]) for r in catchable
            )
            print(f"\nLayer 1 could catch (score < ceiling): {catchable_desc}")
            print(f"  Usable threshold band : ({lower:.4f}, {upper:.4f})   width {upper - lower:.4f}")
            print(f"  Suggested threshold   : {suggested:.2f}")
            if SIMILARITY_THRESHOLD <= lower:
                missed_n = len(catchable)
                print(f"\n  !! The configured {SIMILARITY_THRESHOLD:.2f} is BELOW this band, so Layer 1 "
                      f"catches nothing.")
                print(f"     {missed_n} out-of-scope question(s) reach the model that a "
                      f"{suggested:.2f} threshold would")
                print(f"     have refused for free. Raising it converts {missed_n} LLM call(s) into "
                      f"~ms-latency refusals")
                print(f"     with no loss on the answerable set.")
        else:
            print("\n  No unanswerable question scores below the ceiling — Layer 1 cannot help "
                  "on this set.")

        if uncatchable:
            uncatchable_desc = ", ".join(
                "{}={:.3f}".format(r["id"], r["top_similarity"]) for r in uncatchable
            )
            print(f"\nLayer 2 must handle (score >= ceiling): {uncatchable_desc}")
            print("  These are in-domain questions whose answer simply isn't in the corpus.")
            print("  No similarity threshold can separate them from real questions — retrieval")
            print("  finds genuinely related text; only the model can tell it doesn't answer this.")

    disagreements = [r for r in results if not r["similarity_agreement"]]
    if disagreements:
        print(f"\n  WARNING: logged vs re-run similarity differ for: "
              f"{', '.join(r['id'] for r in disagreements)} (non-deterministic retrieval?)")


def _print_stability(results: list[dict]) -> None:
    """Report run-to-run variance when EVAL_REPEATS > 1.

    The refuse/answer decision is not deterministic even at temperature 0, so a
    single sample can misrepresent a question. Anything below 100% stability is
    a question whose behaviour depends on the roll.
    """
    line = "=" * 108
    print(f"\n{line}\nDECISION STABILITY ACROSS REPEATS\n{line}")
    print("PASS for an unanswerable question = refused, OR answered while explicitly")
    print("flagging the gap. FAIL = answered as if the specific fact were present,")
    print("with no disclaimer — the overconfident-conflation bug.\n")
    print(f"{'id':<5}{'runs':>5}{'pass':>6}{'fail':>6}{'pass rate':>11}{'refuse rate':>13}   {'verdict':<28}")
    print("-" * 82)
    for r in results:
        if "stability" not in r:
            continue
        all_runs = r["all_runs"]
        runs = [x for x in all_runs if x.get("valid", True)]
        invalid = len(all_runs) - len(runs)
        if not runs:
            print(f"{r['id']:<5}{len(all_runs):>5}{'—':>6}{'—':>6}{'INVALID':>11}"
                  f"{'—':>13}   {'ALL RUNS ERRORED':<28}")
            print(f"      {invalid}/{len(all_runs)} runs failed to generate "
                  f"(provider error). No measurement possible.")
            continue
        n = len(runs)
        if r["expected_answerable"]:
            passes = sum(1 for x in runs if not x["refused"])
        else:
            passes = sum(1 for x in runs if x["refused"] or x["gap_flagged"])
        fails = n - passes
        rate = passes / n
        verdict = "stable" if fails == 0 else f"{fails}/{n} FAIL"
        print(f"{r['id']:<5}{n:>5}{passes:>6}{fails:>6}{rate:>10.0%}"
              f"{r['refuse_rate']:>12.0%}   {verdict:<28}")
        if invalid:
            print(f"      NOTE: {invalid} of {len(all_runs)} runs discarded "
                  f"(generation error); rate is over the {n} valid runs only.")

        confs: dict[str, int] = {}
        for x in runs:
            confs[x["confidence"]] = confs.get(x["confidence"], 0) + 1
        print(f"      confidence spread: "
              f"{', '.join(f'{k}={v}' for k, v in sorted(confs.items()))}")
        if fails:
            print("      FAILING RUNS:")
            for i, x in enumerate(runs, start=1):
                bad = (not x["refused"] and not x["gap_flagged"]) if not r["expected_answerable"] \
                    else x["refused"]
                if bad:
                    print(f"        run {i}: refused={x['refused']}, "
                          f"confidence={x['confidence']}, gap_flagged={x['gap_flagged']}")


async def run_eval() -> None:
    """Load the eval test set, query the API for each question, and report scores."""
    cases = json.loads(TEST_SET.read_text(encoding="utf-8"))

    # EVAL_ONLY=q5 (or a comma-separated list) restricts the run to those ids.
    # Useful for probing one question at high repeat count without spending the
    # token budget on the whole set.
    only = [i.strip() for i in os.environ.get("EVAL_ONLY", "").split(",") if i.strip()]
    if only:
        cases = [c for c in cases if c["id"] in only]
        if not cases:
            raise SystemExit(f"EVAL_ONLY={only} matched no test-set ids.")
        print(f"MODE: restricted to {', '.join(c['id'] for c in cases)}\n")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        documents = await _load_documents(conn)
        for case in cases:
            if case.get("expected_doc"):
                _resolve_alias(case["expected_doc"], documents)  # fail fast on bad aliases

        offline = os.environ.get("EVAL_OFFLINE", "") == "1"
        repeats = 1 if offline else int(os.environ.get("EVAL_REPEATS", "1"))
        if offline:
            print("MODE: OFFLINE re-score of stored answers (no API calls, no tokens spent).")
            print("      Rows may come from different runs; timestamps are listed per question.\n")
        results = []
        async with httpx.AsyncClient() as client:
            for i, case in enumerate(cases, start=1):
                print(f"[{i}/{len(cases)}] {case['id']}: {case['question'][:66]}...", flush=True)
                runs = [await run_case(client, conn, case, documents, offline) for _ in range(repeats)]
                primary = runs[0]
                if repeats > 1:
                    refusals = sum(1 for r in runs if r["refused"])
                    majority = refusals > repeats / 2
                    primary["stability"] = max(refusals, repeats - refusals) / repeats
                    primary["refuse_rate"] = refusals / repeats
                    primary["all_runs"] = [
                        {"refused": r["refused"], "confidence": r["confidence"],
                         "gap_flagged": r["gap_flagged"], "valid": r["valid"]} for r in runs
                    ]
                    # Score the majority behaviour rather than one sample.
                    primary["decision_correct"] = majority == (not case["expected_answerable"])
                results.append(primary)
    finally:
        await conn.close()

    print_report(results)
    if any("stability" in r for r in results):
        _print_stability(results)
    RESULTS_OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nFull per-question detail written to {RESULTS_OUT}")


if __name__ == "__main__":
    asyncio.run(run_eval())

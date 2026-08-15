"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export type IndexedDocument = {
  id: number;
  doc_id: string;
  title: string;
  issuer: string;
  doc_date: string;
  status_note: string | null;
  source_url: string | null;
  filename: string;
};

// Plain-English "what is this actually about", keyed by doc_id. The titles are
// the circulars' own — accurate but written in regulator voice, and several are
// near-identical ("Safer participation of retail investors in Algorithmic
// trading" names three different documents here). These say what each one adds.
//
// Deliberately the only hardcoded thing in this component: everything factual
// (which documents exist, their dates, issuers, links) comes from the API, so
// adding a document can never leave the list stale — only un-annotated, which
// falls back gracefully to the circular's own title.
const SUMMARIES: Record<string, string> = {
  "CIR/MRD/DP/09/2012":
    "The original algo rulebook: defines what counts as an algo order, and the risk controls exchanges and brokers must run.",
  "SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013":
    "The framework everything else here implements — API access, algo registration, and who is responsible for what.",
  "SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/46":
    "First deadline extension: pushed back the date for finalising implementation standards.",
  "NSE/INVG/67858 (Circular Ref. No. 471/2025)":
    "NSE's client-facing standards — static IP rules, the 10 orders/second threshold, two-factor authentication.",
  "NSE/INVG/69255 (Circular Ref. No. 495/2025)":
    "How algo providers get empanelled and algos get registered, including the exchange's turnaround times.",
  "NSE/INVG/69289 (Circular Ref. No. 496/2025)":
    "Corrigendum revising the order-tagging (NNF ID) tables set out two days earlier.",
  "SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/132":
    "The glide path: three milestones between October 2025 and January 2026, full compliance by April 2026.",
  "NSE FAQ — Safer participation of Retail investors in Algorithmic trading":
    "NSE answering what members actually asked — who needs a static IP, black box hosting, permitted order types.",
  "MCX Circular (Reminder), referencing MCX/CTCL/235/2025, MCX/CTCL/364/2025, MCX/CTCL/504/2025":
    "MCX reminding brokers of the milestone dates, and what happens to those who miss them.",
};

/** Short issuer label from the full legal name stored on the document. */
function issuerLabel(issuer: string): string {
  if (issuer.includes("SEBI") || issuer.includes("Securities and Exchange Board")) return "SEBI";
  if (issuer.includes("NSE") || issuer.includes("National Stock Exchange")) return "NSE";
  if (issuer.includes("MCX") || issuer.includes("Multi Commodity")) return "MCX";
  return issuer.split(/[,(]/)[0].trim();
}

/** The `source` field records provenance, which is not always just a bare URL —
 *  some entries append a note (e.g. which circular a mirror reproduces). Split
 *  the two so the link stays valid and the note isn't lost. */
function splitSource(source: string | null): { href: string | null; host: string | null } {
  if (!source) return { href: null, host: null };
  const href = source.trim().split(/\s+/)[0];
  if (!/^https?:\/\//.test(href)) return { href: null, host: null };
  try {
    return { href, host: new URL(href).hostname.replace(/^www\./, "") };
  } catch {
    return { href, host: null };
  }
}

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${d} ${months[Number(m) - 1]} ${y}`;
}

export function useIndexedDocuments() {
  const [docs, setDocs] = useState<IndexedDocument[]>([]);

  useEffect(() => {
    if (!API_URL) return;
    let cancelled = false;
    fetch(`${API_URL}/documents`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: IndexedDocument[]) => {
        if (!cancelled) setDocs(data);
      })
      // Silent: the corpus list is supporting context, not the app's job. A
      // failed fetch (or a backend still waking from cold start) collapses the
      // card rather than pushing an error at someone who came here to ask a
      // question.
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  return docs;
}

export default function SourcesCard({ docs }: { docs: IndexedDocument[] }) {
  if (docs.length === 0) return null;

  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="mb-1 flex items-baseline justify-between">
        <h2 className="text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-3">
          Indexed documents
        </h2>
        <span className="text-[11px] tabular-nums text-ink-3">{docs.length}</span>
      </div>
      <p className="mb-3 text-[11.5px] leading-relaxed text-ink-3">
        Every answer is grounded in these and cited to a section.
      </p>

      {/* Capped so the whole card stays inside a laptop viewport rather than
          running past the fold; the rail is sticky, so this list is what
          scrolls, not the page. */}
      <ul className="scroll-thin -mr-1 max-h-[52vh] space-y-3 overflow-y-auto pr-1">
        {docs.map((doc) => {
          const { href, host } = splitSource(doc.source_url);
          const summary = SUMMARIES[doc.doc_id] ?? doc.title;
          return (
            <li key={doc.id} className="border-b border-line pb-3 last:border-0 last:pb-0">
              <div className="mb-1 flex items-center gap-2">
                <span className="rounded border border-line-2 px-1.5 py-px text-[10px] font-medium tracking-wide text-ink-2">
                  {issuerLabel(doc.issuer)}
                </span>
                <span className="text-[11px] tabular-nums text-ink-3">
                  {formatDate(doc.doc_date)}
                </span>
              </div>
              <p className="text-[12.5px] leading-snug text-ink-2">{summary}</p>
              {href && (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-[11px] text-ink-3 underline
                             decoration-line-2 underline-offset-2 transition-colors hover:text-ink"
                >
                  {host ?? "source"}
                  <span aria-hidden>↗</span>
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

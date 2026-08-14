import type { Citation } from "@/components/AnswerCard";

/** Shorten the middle of a long doc_id; the full value stays in the tooltip. */
function truncateDocId(docId: string, max = 26): string {
  if (docId.length <= max) return docId;
  const head = docId.slice(0, max - 12);
  const tail = docId.slice(-9);
  return `${head}…${tail}`;
}

/** Issuers arrive as full legal names; show the recognisable short form. */
function shortIssuer(issuer: string): string {
  const match = issuer.match(/\b(SEBI|NSE|MCX|BSE|NCDEX)\b/);
  if (match) return match[1];
  return issuer.length > 22 ? `${issuer.slice(0, 21)}…` : issuer;
}

/** Sections may carry a long "<number> — <title>" label; keep the number. */
function shortSection(section: string, max = 20): string {
  if (section.length <= max) return section;
  return `${section.slice(0, max - 1).trimEnd()}…`;
}

export default function CitationChip({ citation }: { citation: Citation }) {
  const full = `${citation.issuer} · ${citation.doc_id} · §${citation.section}`;
  return (
    <span
      title={full}
      className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-line
                 bg-surface-2 px-2 py-1 text-[11px] leading-none text-ink-dim
                 transition-colors hover:border-zinc-600 hover:text-ink"
    >
      <span className="font-medium text-ink">{shortIssuer(citation.issuer)}</span>
      <span aria-hidden className="text-ink-faint">·</span>
      <span className="font-mono text-[10px] text-ink-dim">
        {truncateDocId(citation.doc_id)}
      </span>
      <span aria-hidden className="text-ink-faint">·</span>
      <span className="whitespace-nowrap font-mono text-[10px] text-ink-dim">
        §{shortSection(citation.section)}
      </span>
    </span>
  );
}

import type { Citation } from "@/components/AnswerCard";

/** Shorten the middle of a long doc_id; the full value stays in the tooltip. */
function truncateDocId(docId: string, max = 24): string {
  if (docId.length <= max) return docId;
  const head = docId.slice(0, max - 11);
  const tail = docId.slice(-8);
  return `${head}…${tail}`;
}

/** Issuers arrive as full legal names; show the recognisable short form. */
function shortIssuer(issuer: string): string {
  const match = issuer.match(/\b(SEBI|NSE|MCX|BSE|NCDEX)\b/);
  if (match) return match[1];
  return issuer.length > 20 ? `${issuer.slice(0, 19)}…` : issuer;
}

/** Sections may carry a long "<number> — <title>" label; keep the number. */
function shortSection(section: string, max = 22): string {
  if (section.length <= max) return section;
  return `${section.slice(0, max - 1).trimEnd()}…`;
}

/** Issuer-coded accent, so a mixed-source answer is scannable at a glance. */
const ISSUER_TONE: Record<string, string> = {
  SEBI: "bg-[#EEF4FF] text-[#1F4FA8] ring-[#D6E2FA]",
  NSE: "bg-[#F1F0FB] text-[#4A3F9E] ring-[#DFDCF3]",
  MCX: "bg-[#FDF2EC] text-[#9A5320] ring-[#F5DFCE]",
};

export default function CitationChip({ citation }: { citation: Citation }) {
  const issuer = shortIssuer(citation.issuer);
  const tone = ISSUER_TONE[issuer] ?? "bg-surface-2 text-ink-2 ring-line-2";
  const full = `${citation.issuer} · ${citation.doc_id} · §${citation.section}`;

  return (
    <span
      title={full}
      className="inline-flex max-w-full items-center gap-2 rounded-full border border-line-2
                 bg-surface py-1 pl-1 pr-3 transition-colors hover:border-ink-4"
    >
      <span
        className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase
                    tracking-[0.06em] ring-1 ring-inset ${tone}`}
      >
        {issuer}
      </span>
      <span className="min-w-0 truncate font-mono text-[10.5px] leading-none text-ink-3">
        {truncateDocId(citation.doc_id)}
      </span>
      <span aria-hidden className="text-ink-4">
        ·
      </span>
      <span className="shrink-0 whitespace-nowrap text-[11px] font-medium leading-none text-ink-2">
        §{shortSection(citation.section)}
      </span>
    </span>
  );
}

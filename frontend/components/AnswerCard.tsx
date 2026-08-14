import CitationChip from "@/components/CitationChip";

export type Citation = {
  doc_id: string;
  issuer: string;
  section: string;
};

export type Confidence = "high" | "medium" | "low";

export type ComplianceAnswer = {
  answer: string;
  citations: Citation[];
  confidence: Confidence;
  refused: boolean;
};

const CONFIDENCE_STYLES: Record<Confidence, { dot: string; chip: string; label: string }> = {
  high: {
    dot: "bg-emerald-400",
    chip: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    label: "High confidence",
  },
  medium: {
    dot: "bg-amber-400",
    chip: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    label: "Medium confidence",
  },
  low: {
    dot: "bg-red-400",
    chip: "border-red-500/30 bg-red-500/10 text-red-300",
    label: "Low confidence",
  },
};

function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const style = CONFIDENCE_STYLES[confidence];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-xs font-medium ${style.chip}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden />
      {style.label}
    </span>
  );
}

function Citations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-5 border-t border-line-soft pt-4">
      <p className="mb-2.5 text-[11px] font-medium uppercase tracking-wider text-ink-faint">
        Sources · {citations.length}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((citation, i) => (
          <CitationChip key={`${citation.doc_id}-${citation.section}-${i}`} citation={citation} />
        ))}
      </div>
    </div>
  );
}

export default function AnswerCard({ result }: { result: ComplianceAnswer }) {
  // Refused answers get their own card treatment — amber-tinted surface, a
  // warning glyph and an explicit heading — so the state reads at a glance
  // rather than depending on the reader parsing the prose.
  if (result.refused) {
    return (
      <article className="fade-rise rounded-lg border border-amber-500/25 bg-amber-500/[0.06] p-5">
        <header className="mb-3 flex items-center gap-2.5">
          <span
            aria-hidden
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full
                       border border-amber-500/40 bg-amber-500/15 text-[13px] text-amber-300"
          >
            !
          </span>
          <h2 className="text-sm font-semibold text-amber-200">
            Not covered by these documents
          </h2>
        </header>
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-amber-100/80">
          {result.answer}
        </p>
        <Citations citations={result.citations} />
      </article>
    );
  }

  return (
    <article className="fade-rise rounded-lg border border-line bg-surface-1 p-5">
      <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink">
        {result.answer}
      </p>
      <div className="mt-4">
        <ConfidenceBadge confidence={result.confidence} />
      </div>
      <Citations citations={result.citations} />
    </article>
  );
}

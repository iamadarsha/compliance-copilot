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
    dot: "bg-good-ink",
    chip: "border-good-line bg-good-bg text-good-ink",
    label: "High confidence",
  },
  medium: {
    dot: "bg-warn-ink",
    chip: "border-warn-line bg-warn-bg text-warn-ink",
    label: "Medium confidence",
  },
  low: {
    dot: "bg-bad-ink",
    chip: "border-bad-line bg-bad-bg text-bad-ink",
    label: "Low confidence",
  },
};

function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const style = CONFIDENCE_STYLES[confidence];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${style.chip}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden />
      {style.label}
    </span>
  );
}

function Citations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-6 border-t border-line-2 pt-5">
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-3">
        Sources · {citations.length}
      </p>
      <div className="flex flex-wrap gap-2">
        {citations.map((citation, i) => (
          <CitationChip key={`${citation.doc_id}-${citation.section}-${i}`} citation={citation} />
        ))}
      </div>
    </div>
  );
}

export default function AnswerCard({ result }: { result: ComplianceAnswer }) {
  // The refused state gets its own surface treatment — warm tint, ruled left
  // edge, warning glyph and an explicit heading — so "the documents don't cover
  // this" reads instantly, rather than depending on the reader parsing prose.
  if (result.refused) {
    return (
      <article
        className="fade-rise overflow-hidden rounded-2xl border border-warn-line bg-warn-bg
                   shadow-card"
      >
        <div className="border-l-[3px] border-warn-ink/40 px-6 py-5 sm:px-7 sm:py-6">
          <header className="mb-3 flex items-center gap-2.5">
            <span
              aria-hidden
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full
                         bg-warn-ink/12 text-[13px] font-bold text-warn-ink"
            >
              !
            </span>
            <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-warn-ink">
              Not covered by these documents
            </h2>
          </header>
          <p className="whitespace-pre-wrap text-[15px] leading-[1.65] text-ink">
            {result.answer}
          </p>
          <Citations citations={result.citations} />
        </div>
      </article>
    );
  }

  return (
    <article
      className="fade-rise rounded-2xl border border-line bg-surface px-6 py-6 shadow-card
                 sm:px-7 sm:py-7"
    >
      <p className="whitespace-pre-wrap text-[16px] leading-[1.65] tracking-[-0.005em] text-ink">
        {result.answer}
      </p>
      <div className="mt-5">
        <ConfidenceBadge confidence={result.confidence} />
      </div>
      <Citations citations={result.citations} />
    </article>
  );
}

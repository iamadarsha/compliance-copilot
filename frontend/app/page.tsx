"use client";

import { useState } from "react";

import AnswerCard, { type ComplianceAnswer } from "@/components/AnswerCard";
import QueryBox, { type Prefill } from "@/components/QueryBox";
import SourcesCard, { useIndexedDocuments } from "@/components/SourcesCard";

type HistoryEntry = {
  id: number;
  question: string;
  result: ComplianceAnswer;
};

// Orientation questions, answered deterministically from the indexed corpus
// rather than by retrieval (see backend app/rag/meta.py). Listed first because
// someone who has never seen this needs to know what it covers before a
// question about order-per-second thresholds means anything to them.
const STARTER_EXAMPLES = ["What can you do?", "What circulars do you have?"];

// Every example here is verified to clear the 0.69 retrieval threshold (scores
// 0.71 / 0.74 / 0.76) — an example that lands in a refusal would make a
// working system look broken to anyone trying it for the first time.
// "Who counts as 'family'?" alone scores 0.56 and is deliberately NOT used.
const EXAMPLES = [
  "Max orders per second?",
  "Who counts as 'family' for sharing a registered algo?",
  "When does it apply to all brokers?",
];

/** Status dot mirroring the answer's outcome, for the history rail. */
function OutcomeDot({ result }: { result: ComplianceAnswer }) {
  const tone = result.refused
    ? "bg-warn-ink"
    : result.confidence === "high"
      ? "bg-good-ink"
      : result.confidence === "medium"
        ? "bg-warn-ink"
        : "bg-bad-ink";
  return <span className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${tone}`} aria-hidden />;
}

function Logo() {
  return (
    <span
      aria-hidden
      className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-white"
    >
      <svg
        viewBox="0 0 24 24"
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 3l7 3v5.5c0 4.6-3 8-7 9.5-4-1.5-7-4.9-7-9.5V6z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    </span>
  );
}

export default function Home() {
  // Session-only history. Deliberately in-memory: the backend already persists
  // every query, and browsing past sessions is outside this assignment's scope.
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [prefill, setPrefill] = useState<Prefill | null>(null);
  const docs = useIndexedDocuments();

  function handleResult(question: string, result: ComplianceAnswer) {
    const entry: HistoryEntry = { id: Date.now(), question, result };
    setHistory((prev) => [entry, ...prev]);
    setSelectedId(entry.id);
  }

  const selected = history.find((h) => h.id === selectedId) ?? history[0] ?? null;

  return (
    <div className="min-h-screen">
      <header className="chrome-blur sticky top-0 z-20 border-b border-line">
        <div className="mx-auto flex min-h-[60px] max-w-[1080px] items-center justify-between gap-3 px-5 sm:px-7">
          <div className="flex items-center gap-2.5">
            <Logo />
            {/* nowrap: with two rail toggles in the header, a phone-width
                viewport otherwise breaks the product name across two lines. */}
            <h1 className="whitespace-nowrap text-[16px] font-semibold tracking-[-0.02em] text-ink">
              Compliance Copilot
            </h1>
            <span className="hidden text-[12px] text-ink-3 sm:inline">
              SEBI · NSE · MCX
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Count comes from the API, never a literal. It was hardcoded once
                and kept saying "5 circulars indexed" long after the corpus grew
                to 9 — nothing tied the claim to the data. */}
            {docs.length > 0 && (
              <span className="hidden rounded-full border border-line-2 bg-surface px-2.5 py-1 text-[11px] text-ink-2 lg:inline">
                {docs.length} circulars indexed
              </span>
            )}
            {docs.length > 0 && (
              <button
                onClick={() => setSourcesOpen((v) => !v)}
                aria-expanded={sourcesOpen}
                className="flex min-h-9 shrink-0 items-center whitespace-nowrap rounded-full border
                           border-line-2 bg-surface px-3 text-[12px] font-medium text-ink-2
                           transition-colors hover:border-ink-4 hover:text-ink lg:hidden"
              >
                Sources<span className="hidden sm:inline">&nbsp;({docs.length})</span>
              </button>
            )}
            <button
              onClick={() => setHistoryOpen((v) => !v)}
              aria-expanded={historyOpen}
              className="flex min-h-9 shrink-0 items-center whitespace-nowrap rounded-full border
                         border-line-2 bg-surface px-3 text-[12px] font-medium text-ink-2
                         transition-colors hover:border-ink-4 hover:text-ink lg:hidden"
            >
              History{history.length > 0 && ` (${history.length})`}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1240px] px-5 pb-20 pt-10 sm:px-7 sm:pt-14">
        {/* Hero — collapses once there's an answer, so results lead the page. */}
        {!selected && (
          <div className="mx-auto mb-8 max-w-2xl text-center">
            <h2 className="text-[28px] font-semibold leading-[1.15] tracking-[-0.03em] text-ink sm:text-[34px]">
              Answers from the circulars,
              <br className="hidden sm:block" /> never from guesswork.
            </h2>
            <p className="mx-auto mt-3.5 max-w-lg text-[15px] leading-relaxed text-ink-2">
              Ask about retail algorithmic trading obligations. Every answer is grounded in
              the loaded SEBI, NSE and MCX circulars and cited to a section — questions the
              documents don&apos;t cover are declined rather than guessed.
            </p>
          </div>
        )}

        {/* Three columns on desktop. The left rail was originally an empty
            spacer mirroring the history rail, purely so the centre column stayed
            optically centred — the search bar, answer card and example chips all
            share one axis, and without it the aside drags everything left of the
            hero above it. It now carries the corpus list, which needed a home
            that is visible without a click and keeps that same width. Below lg
            both rails collapse and are toggled from the header, so the question
            box stays first on a phone. */}
        <div className="flex flex-col gap-8 lg:flex-row lg:justify-center lg:gap-8">
          <div
            className={`w-full shrink-0 lg:sticky lg:top-[76px] lg:block lg:h-fit lg:w-[260px]
                        ${sourcesOpen ? "block" : "hidden"}`}
            aria-label="Indexed documents"
          >
            <SourcesCard docs={docs} />
          </div>

          <main className="w-full min-w-0 lg:w-[640px] lg:shrink-0">
            <QueryBox onResult={handleResult} prefill={prefill} />

            <div className="mt-8">
            {selected ? (
              <>
                <p className="mb-3.5 text-[13px] leading-relaxed text-ink-2">
                  <span className="font-medium uppercase tracking-[0.07em] text-ink-3">
                    Question ·{" "}
                  </span>
                  {selected.question}
                </p>
                <AnswerCard result={selected.result} />
              </>
            ) : (
              <div className="flex flex-col gap-6">
                <div>
                  <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-3">
                    New here
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {STARTER_EXAMPLES.map((example) => (
                      <button
                        key={example}
                        onClick={() => setPrefill({ value: example, key: Date.now() })}
                        className="rounded-full border border-line-2 bg-surface px-4 py-2.5 text-[13px]
                                   text-ink-2 shadow-sm transition-all hover:-translate-y-px
                                   hover:border-ink-4 hover:text-ink"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-[0.09em] text-ink-3">
                    Ask the circulars
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {EXAMPLES.map((example) => (
                      <button
                        key={example}
                        onClick={() => setPrefill({ value: example, key: Date.now() })}
                        className="rounded-full border border-line-2 bg-surface px-4 py-2.5 text-[13px]
                                   text-ink-2 shadow-sm transition-all hover:-translate-y-px
                                   hover:border-ink-4 hover:text-ink"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            </div>
          </main>

          <aside
            className={`w-full shrink-0 lg:block lg:w-[260px] ${historyOpen ? "block" : "hidden"}`}
            aria-label="Session history"
          >
            <div className="rounded-2xl border border-line bg-surface p-4">
              <div className="mb-3 flex items-baseline justify-between">
                <h2 className="text-[10px] font-semibold uppercase tracking-[0.09em] text-ink-3">
                  This session
                </h2>
                {history.length > 0 && (
                  <span className="text-[11px] tabular-nums text-ink-3">{history.length}</span>
                )}
              </div>

              {history.length === 0 ? (
                <p className="text-[12.5px] leading-relaxed text-ink-3">
                  Questions you ask will be listed here. History isn&apos;t persisted across
                  reloads.
                </p>
              ) : (
                <ul className="scroll-thin -mr-1 max-h-[58vh] space-y-0.5 overflow-y-auto pr-1">
                  {history.map((entry) => {
                    const active = entry.id === selected?.id;
                    return (
                      <li key={entry.id}>
                        <button
                          onClick={() => setSelectedId(entry.id)}
                          className={`flex w-full items-start gap-2.5 rounded-xl px-3 py-2.5 text-left
                                      text-[12.5px] leading-snug transition-colors ${
                                        active
                                          ? "bg-canvas font-medium text-ink"
                                          : "text-ink-2 hover:bg-canvas hover:text-ink"
                                      }`}
                        >
                          <OutcomeDot result={entry.result} />
                          <span className="line-clamp-2 min-w-0">{entry.question}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

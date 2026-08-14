"use client";

import { useState } from "react";

import AnswerCard, { type ComplianceAnswer } from "@/components/AnswerCard";
import QueryBox from "@/components/QueryBox";

type HistoryEntry = {
  id: number;
  question: string;
  result: ComplianceAnswer;
};

/** Small status dot mirroring the answer's outcome, for the history list. */
function OutcomeDot({ result }: { result: ComplianceAnswer }) {
  const tone = result.refused
    ? "bg-amber-400"
    : result.confidence === "high"
      ? "bg-emerald-400"
      : result.confidence === "medium"
        ? "bg-amber-400"
        : "bg-red-400";
  return <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${tone}`} aria-hidden />;
}

export default function Home() {
  // Session-only history. Deliberately in-memory: the backend already persists
  // every query, and browsing past sessions is outside this assignment's scope.
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [historyOpen, setHistoryOpen] = useState(true);

  function handleResult(question: string, result: ComplianceAnswer) {
    const entry: HistoryEntry = { id: Date.now(), question, result };
    setHistory((prev) => [entry, ...prev]);
    setSelectedId(entry.id);
  }

  const selected = history.find((h) => h.id === selectedId) ?? history[0] ?? null;

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-5 py-8 lg:px-8">
      <header className="mb-7 flex items-baseline justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-ink">Compliance Copilot</h1>
          <p className="mt-1 text-[13px] text-ink-dim">
            Grounded answers on retail algorithmic trading, cited to SEBI, NSE and MCX circulars.
          </p>
        </div>
        <button
          onClick={() => setHistoryOpen((v) => !v)}
          className="flex min-h-11 shrink-0 items-center rounded-md border border-line px-3.5
                     text-xs text-ink-dim transition-colors hover:border-zinc-600 hover:text-ink lg:hidden"
          aria-expanded={historyOpen}
        >
          History {history.length > 0 && `(${history.length})`}
        </button>
      </header>

      <div className="flex flex-1 flex-col gap-7 lg:flex-row lg:gap-8">
        <main className="min-w-0 lg:flex-1">
          <QueryBox onResult={handleResult} />

          <div className="mt-6">
            {selected ? (
              <>
                <p className="mb-3 text-[13px] text-ink-dim">
                  <span className="text-ink-faint">Question · </span>
                  {selected.question}
                </p>
                <AnswerCard result={selected.result} />
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-line px-5 py-10 text-center">
                <p className="text-[13px] text-ink-dim">
                  Ask a question to get started.
                </p>
                <p className="mx-auto mt-2 max-w-md text-[13px] leading-relaxed text-ink-faint">
                  Every answer is drawn only from the loaded circulars. Questions the
                  documents don&apos;t cover are declined rather than guessed.
                </p>
              </div>
            )}
          </div>
        </main>

        <aside
          className={`w-full shrink-0 lg:block lg:w-72 ${historyOpen ? "block" : "hidden"}`}
          aria-label="Session history"
        >
          <div className="flex items-baseline justify-between">
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">
              This session
            </h2>
            {history.length > 0 && (
              <span className="text-[11px] text-ink-faint">{history.length}</span>
            )}
          </div>

          {history.length === 0 ? (
            <p className="mt-3 text-[13px] leading-relaxed text-ink-faint">
              Questions you ask will be listed here. History is not persisted across reloads.
            </p>
          ) : (
            <ul className="scroll-thin mt-3 max-h-[60vh] space-y-1 overflow-y-auto pr-1">
              {history.map((entry) => {
                const active = entry.id === selected?.id;
                return (
                  <li key={entry.id}>
                    <button
                      onClick={() => setSelectedId(entry.id)}
                      className={`flex w-full items-start gap-2 rounded-md border px-2.5 py-2
                                  text-left text-[13px] leading-snug transition-colors ${
                                    active
                                      ? "border-line bg-surface-2 text-ink"
                                      : "border-transparent text-ink-dim hover:bg-surface-1 hover:text-ink"
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
        </aside>
      </div>
    </div>
  );
}

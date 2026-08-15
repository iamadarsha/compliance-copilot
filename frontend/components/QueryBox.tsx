"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { ComplianceAnswer } from "@/components/AnswerCard";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// Generation runs 1-18s against Groq. A static spinner reads as a hang at that
// duration, so the status line advances through the pipeline's real stages.
const STAGES = [
  "Retrieving relevant sections…",
  "Ranking passages by similarity…",
  "Checking grounding…",
  "Composing a cited answer…",
] as const;
const STAGE_MS = 3200;

export type Prefill = { value: string; key: number };

export type QueryBoxProps = {
  onResult: (question: string, result: ComplianceAnswer) => void;
  /** Set by an example-question click; `key` changes so the same text re-fires. */
  prefill?: Prefill | null;
};

export default function QueryBox({ onResult, prefill }: QueryBoxProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const loadingRef = useRef(false);

  useEffect(() => {
    if (!loading) {
      if (timer.current) clearInterval(timer.current);
      return;
    }
    setStage(0);
    timer.current = setInterval(
      () => setStage((s) => Math.min(s + 1, STAGES.length - 1)),
      STAGE_MS,
    );
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [loading]);

  const ask = useCallback(
    async (raw: string) => {
      const trimmed = raw.trim();
      // loadingRef, not the `loading` state, because an example click can fire
      // from an effect before React has re-rendered with the new state.
      if (!trimmed || loadingRef.current) return;

      if (!API_URL) {
        setError(
          "NEXT_PUBLIC_API_URL is not set. Copy frontend/.env.local.example to " +
            "frontend/.env.local and restart the dev server.",
        );
        return;
      }

      loadingRef.current = true;
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_URL}/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: trimmed }),
        });
        if (!response.ok) {
          // A non-2xx is a transport/server failure, NOT a refused answer —
          // surfaced as an error state so the two can never be confused.
          throw new Error(`Backend returned ${response.status} ${response.statusText}`);
        }
        const result: ComplianceAnswer = await response.json();
        onResult(trimmed, result);
        setQuestion("");
      } catch (err) {
        setError(
          err instanceof Error
            ? `${err.message}. Is the backend running at ${API_URL}?`
            : "Unexpected error contacting the backend.",
        );
      } finally {
        loadingRef.current = false;
        setLoading(false);
      }
    },
    [onResult],
  );

  // An example-question click both fills the box and submits it.
  useEffect(() => {
    if (!prefill) return;
    setQuestion(prefill.value);
    void ask(prefill.value);
    // Keyed on `prefill.key` so clicking the same example twice re-fires.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill?.key]);

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <div
          className="search-shell flex items-center gap-2 rounded-full border border-line bg-surface
                     py-2 pl-5 pr-2 shadow-search transition-shadow"
        >
          <svg
            aria-hidden
            viewBox="0 0 24 24"
            className="h-[18px] w-[18px] shrink-0 text-ink-3"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              // Explicit rather than relying solely on native browser
              // submit-on-Enter for a text input in a form: that behavior
              // proved unreliable in testing (some browsers/environments
              // don't trigger it from a synthetic or IME-composed keypress),
              // and Enter-to-submit is basic enough behavior for a single-field
              // form that leaving it to chance isn't acceptable.
              if (e.key === "Enter" && !e.nativeEvent.isComposing) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
            disabled={loading}
            maxLength={500}
            placeholder="Ask about SEBI, NSE or MCX algo-trading obligations…"
            aria-label="Compliance question"
            className="min-w-0 flex-1 bg-transparent py-2 text-[15px] text-ink outline-none
                       placeholder:text-ink-3 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            aria-label="Ask"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent
                       text-white transition-all hover:bg-accent-dark active:scale-95
                       disabled:cursor-not-allowed disabled:bg-ink-4 disabled:active:scale-100"
          >
            {loading ? (
              <span className="flex gap-[3px]" aria-hidden>
                {[0, 160, 320].map((d) => (
                  <span
                    key={d}
                    className="pulse-dot h-1 w-1 rounded-full bg-white"
                    style={{ animationDelay: `${d}ms` }}
                  />
                ))}
              </span>
            ) : (
              <svg
                aria-hidden
                viewBox="0 0 24 24"
                className="h-[18px] w-[18px]"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h13M13 6l6 6-6 6" />
              </svg>
            )}
          </button>
        </div>
      </form>

      {loading && (
        <div
          role="status"
          aria-live="polite"
          className="mt-4 flex items-center justify-center gap-2 text-[13px] text-ink-2"
        >
          <span className="flex gap-1" aria-hidden>
            {[0, 160, 320].map((d) => (
              <span
                key={d}
                className="pulse-dot h-1.5 w-1.5 rounded-full bg-accent"
                style={{ animationDelay: `${d}ms` }}
              />
            ))}
          </span>
          <span>{STAGES[stage]}</span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="fade-rise mt-4 flex items-start gap-3 rounded-2xl border border-bad-line
                     bg-bad-bg px-4 py-3.5"
        >
          <span
            aria-hidden
            className="mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded-full
                       bg-bad-ink/12 text-[11px] font-bold text-bad-ink"
          >
            ×
          </span>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-bad-ink">Request failed</p>
            <p className="mt-0.5 break-words text-[13px] leading-relaxed text-ink-2">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}

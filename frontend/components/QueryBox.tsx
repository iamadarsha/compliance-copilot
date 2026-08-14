"use client";

import { useEffect, useRef, useState } from "react";

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

export type QueryBoxProps = {
  onResult: (question: string, result: ComplianceAnswer) => void;
};

export default function QueryBox({ onResult }: QueryBoxProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

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

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    if (!API_URL) {
      setError(
        "NEXT_PUBLIC_API_URL is not set. Copy frontend/.env.local.example to " +
          "frontend/.env.local and restart the dev server.",
      );
      return;
    }

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
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="flex gap-2">
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
          className="field min-w-0 flex-1 rounded-lg border border-line bg-surface-1 px-3.5 py-2.5
                     text-[15px] text-ink placeholder:text-ink-faint
                     transition-colors disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="shrink-0 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white
                     transition-opacity hover:opacity-90
                     disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Working…" : "Ask"}
        </button>
      </form>

      {loading && (
        <div
          role="status"
          aria-live="polite"
          className="mt-3 flex items-center gap-2.5 text-[13px] text-ink-dim"
        >
          <span className="flex gap-1" aria-hidden>
            {[0, 150, 300].map((delay) => (
              <span
                key={delay}
                className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent"
                style={{ animationDelay: `${delay}ms` }}
              />
            ))}
          </span>
          <span>{STAGES[stage]}</span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="fade-rise mt-3 flex items-start gap-2.5 rounded-lg border border-red-500/30
                     bg-red-500/[0.07] px-3.5 py-3"
        >
          <span
            aria-hidden
            className="mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded-full
                       border border-red-500/40 bg-red-500/15 text-[11px] font-bold text-red-300"
          >
            ×
          </span>
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-red-200">Request failed</p>
            <p className="mt-0.5 break-words text-[13px] leading-relaxed text-red-200/70">
              {error}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

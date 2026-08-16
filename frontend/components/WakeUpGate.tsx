"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

/** Roughly how long a Render free-tier cold start takes. Used only to pace the
 *  bar between real checkpoints — never to claim readiness the app hasn't
 *  actually confirmed. */
const EXPECTED_WAKE_MS = 50_000;
const POLL_MS = 1_500;

type Phase = "connecting" | "waking" | "loading-corpus" | "ready" | "unreachable";

const PHASE_COPY: Record<Exclude<Phase, "ready">, { title: string; detail: string }> = {
  connecting: {
    title: "Connecting to the backend",
    detail: "Checking whether the API is already awake.",
  },
  waking: {
    title: "Waking the backend",
    detail:
      "The API sleeps after 15 minutes idle on Render's free tier. This happens once — subsequent questions are fast.",
  },
  "loading-corpus": {
    title: "Loading the document index",
    detail: "The API is up. Confirming the circulars are indexed and searchable.",
  },
  unreachable: {
    title: "Backend isn't responding",
    detail:
      "It may still be starting, or the free instance may be rate-limited. You can keep waiting, or try a question anyway.",
  },
};

/**
 * Cold-start status for the deployed backend.
 *
 * Progress here is honest about what it does and does not know. Two checkpoints
 * are real and observed — the API answering `/health`, and `/documents`
 * returning a non-empty corpus — and the bar only completes when both have
 * actually happened. Between them it advances on an easing curve derived from
 * elapsed time, which is an *estimate* and is capped below 100% so it can never
 * imply readiness the app hasn't confirmed. Elapsed seconds are shown alongside
 * so the number is never the only thing the reader has to trust.
 */
export default function WakeUpGate({ onReady }: { onReady?: () => void }) {
  const [phase, setPhase] = useState<Phase>("connecting");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [docCount, setDocCount] = useState<number | null>(null);
  const startedAt = useRef(Date.now());
  const notified = useRef(false);

  useEffect(() => {
    if (!API_URL) {
      setPhase("ready"); // nothing to wait on in a misconfigured local setup
      return;
    }

    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout>;

    const tick = setInterval(() => {
      if (!cancelled) setElapsedMs(Date.now() - startedAt.current);
    }, 250);

    async function poll() {
      if (cancelled) return;
      try {
        const health = await fetch(`${API_URL}/health`, { cache: "no-store" });
        if (!health.ok) throw new Error(String(health.status));

        if (!cancelled) setPhase("loading-corpus");
        const docs = await fetch(`${API_URL}/documents`, { cache: "no-store" });
        const parsed: unknown[] = docs.ok ? await docs.json() : [];

        if (cancelled) return;
        if (parsed.length > 0) {
          setDocCount(parsed.length);
          setPhase("ready");
          if (!notified.current) {
            notified.current = true;
            onReady?.();
          }
          return;
        }
        // API is up but the corpus is empty — keep polling rather than
        // declaring ready, since the app cannot answer anything yet.
        pollTimer = setTimeout(poll, POLL_MS);
      } catch {
        if (cancelled) return;
        const waited = Date.now() - startedAt.current;
        setPhase(waited > EXPECTED_WAKE_MS * 1.8 ? "unreachable" : "waking");
        pollTimer = setTimeout(poll, POLL_MS);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearInterval(tick);
      clearTimeout(pollTimer);
    };
  }, [onReady]);

  if (phase === "ready") return null;

  const seconds = Math.floor(elapsedMs / 1000);
  // Ease-out toward 90%: fast at first, asymptotic after. Deliberately never
  // reaches 100 on estimate alone — only the confirmed-ready state does that,
  // and that state unmounts this component.
  const estimated = 1 - Math.exp(-elapsedMs / (EXPECTED_WAKE_MS * 0.55));
  const percent =
    phase === "loading-corpus" ? 95 : Math.min(90, Math.round(estimated * 90));
  const copy = PHASE_COPY[phase];

  return (
    <div
      className="fade-rise rounded-2xl border border-line bg-surface px-6 py-6 shadow-card sm:px-7"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">{copy.title}</h2>
        <span className="shrink-0 text-[12px] tabular-nums text-ink-3">
          {percent}% · {seconds}s
        </span>
      </div>

      <div
        className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-canvas"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Backend readiness"
      >
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>

      <p className="mt-3 max-w-[62ch] text-[13.5px] leading-relaxed text-ink-2">{copy.detail}</p>

      <ul className="mt-4 flex flex-col gap-1.5">
        <Check done={phase === "loading-corpus"} label="API responding" />
        <Check done={docCount !== null} label="Document index loaded" />
      </ul>
    </div>
  );
}

function Check({ done, label }: { done: boolean; label: string }) {
  return (
    <li className="flex items-center gap-2 text-[12.5px] text-ink-3">
      <span
        aria-hidden
        className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border text-[9px] ${
          done ? "border-good-line bg-good-bg text-good-ink" : "border-line-2 text-ink-3"
        }`}
      >
        {done ? "✓" : ""}
      </span>
      {label}
    </li>
  );
}

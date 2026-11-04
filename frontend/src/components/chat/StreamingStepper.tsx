"use client";

import React, { useEffect, useState } from "react";
import { Check, X, Minus } from "lucide-react";
import { clsx } from "clsx";
import { formatDuration } from "@/lib/format";

/** Human names for the pipeline steps the backend streams. */
const STEP_LABELS: Record<string, string> = {
  understanding_question: "Reading the question",
  retrieving_schema: "Finding the right tables",
  generating_query: "Writing the SQL",
  validating_query: "Checking the SQL is safe",
  running_query: "Running it read-only",
  verifying_results: "Verifying the results",
  composing_answer: "Composing the answer",
  analysing: "Running the analysis",
};

function humanize(token: string): string {
  const spaced = token.replace(/[_-]+/g, " ").trim().toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * Names a step for a reader.
 *
 * The specialist pipelines reuse one step key (`running_query`) for several
 * different stages and put the real stage in the message as a `STAGE:` prefix,
 * so that prefix is preferred when present — otherwise two consecutive rows
 * would carry the same name.
 */
export function labelForStep(step: string, message = ""): { label: string; detail: string } {
  const prefixed = /^([A-Z][A-Z_]{3,}):\s*(.*)$/.exec(message.trim());
  if (prefixed) {
    return { label: humanize(prefixed[1]), detail: prefixed[2] };
  }
  return { label: STEP_LABELS[step] ?? humanize(step), detail: message };
}

export interface StepView {
  /** The backend's step key. Repeats, so never use it as a React key. */
  step: string;
  status: "running" | "succeeded" | "failed" | "skipped";
  message: string;
  /**
   * The backend's own duration. Present only once the final result lands —
   * the live SSE progress events do not carry one.
   */
  durationMs: number | null;
  /** Wall-clock elapsed measured in the browser while the step was running. */
  elapsedMs?: number | null;
}

/** A live wall-clock counter for the step currently running. */
function LiveElapsed({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 100);
    return () => window.clearInterval(id);
  }, []);
  return <span className="num text-label text-muted">{formatDuration(now - since)}</span>;
}

interface StreamingStepperProps {
  steps: StepView[];
  /** When the currently running step began, for the live counter. */
  runningSince?: number | null;
  /** True while the stream is open. */
  live: boolean;
  /** The backend's total, shown once the result lands. */
  totalMs?: number | null;
}

/**
 * Progress being made, as a list that grows.
 *
 * Steps arrive one at a time over SSE, so the list itself is the progress — no
 * bar, no percentage the backend never sent. The only entrance on the screen is
 * a step appearing, and it marks real work rather than decorating a load.
 *
 * `trace_steps` repeats `step` values (`verifying_results` appears twice on a
 * normal run), so rows key on index.
 */
export function StreamingStepper({ steps, runningSince, live, totalMs }: StreamingStepperProps) {
  if (steps.length === 0 && !live) return null;

  return (
    <section
      aria-label="Analysis progress"
      className="plane-raised overflow-hidden"
    >
      <div className="flex items-center justify-between gap-3 border-b border-[var(--rule)] px-5 py-3">
        <h3 className="flex items-center gap-2 text-label font-medium text-text">
          {live ? (
            <span aria-hidden="true" className="pulse-dot relative h-1.5 w-1.5 rounded-full bg-accent" />
          ) : null}
          {live ? "Working" : "How this was answered"}
        </h3>
        {typeof totalMs === "number" ? (
          <span className="num text-label text-muted">{formatDuration(totalMs)} total</span>
        ) : null}
      </div>

      <ol className="divide-y divide-[var(--rule)]" aria-live="polite" aria-atomic="false">
        {steps.map((s, i) => {
          const running = s.status === "running";
          const named = labelForStep(s.step, s.message);
          return (
            <li
              key={`${s.step}-${i}`}
              className="step-in row-responds flex items-baseline gap-3 px-5 py-3"
            >
              <span aria-hidden="true" className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                {s.status === "succeeded" ? (
                  <Check className="h-3.5 w-3.5 text-positive" />
                ) : s.status === "failed" ? (
                  <X className="h-3.5 w-3.5 text-negative" />
                ) : s.status === "skipped" ? (
                  <Minus className="h-3.5 w-3.5 text-faint" />
                ) : (
                  <span className="pulse-ring pulse-dot relative h-1.5 w-1.5 rounded-full bg-accent" />
                )}
              </span>

              <span className="min-w-0 flex-1">
                <span className="block text-body text-text">
                  {named.label}
                  {s.status === "failed" || s.status === "skipped" ? (
                    <span
                      className={clsx(
                        "ml-2 align-middle text-label",
                        s.status === "failed" ? "text-negative" : "text-faint"
                      )}
                    >
                      {s.status}
                    </span>
                  ) : null}
                </span>
                {named.detail ? <span className="block text-label text-muted">{named.detail}</span> : null}
              </span>

              <span className="shrink-0 text-right">
                {typeof s.durationMs === "number" ? (
                  <span className="num text-label text-muted">{formatDuration(s.durationMs)}</span>
                ) : running && runningSince ? (
                  <LiveElapsed since={runningSince} />
                ) : typeof s.elapsedMs === "number" ? (
                  <span className="num text-label text-faint" title="Measured in the browser while the step ran">
                    {/* A browser-measured gap below a millisecond is real, but
                        printing it as "0.00 ms" reads as a broken value. */}
                    {s.elapsedMs < 1 ? "under 1 ms" : formatDuration(s.elapsedMs)}
                  </span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ol>

      {live && steps.length === 0 ? (
        <p className="px-4 py-3 text-body text-muted">Sending the question…</p>
      ) : null}
    </section>
  );
}

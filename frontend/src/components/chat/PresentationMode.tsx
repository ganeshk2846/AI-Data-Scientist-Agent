"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { clsx } from "clsx";
import { ExecutiveSection, ManagementResponse, MultiAgentWorkflowResult } from "@/types/api";
import { Markdown } from "@/components/ui/Markdown";
import { DataTable } from "@/components/ui/DataTable";
import { PlotlyChartRenderer } from "@/components/PlotlyChartRenderer";
import { splitKpis } from "@/components/ui/Stat";
import { formatDuration } from "@/lib/format";
import {
  describeResult,
  firstSentence,
  isUnusableHeadline,
  scopeForValue,
} from "@/lib/narrative";

const SECTION_ORDER: { key: keyof ManagementResponse; name: string }[] = [
  { key: "what", name: "What" },
  { key: "why", name: "Why" },
  { key: "so_what", name: "So what" },
  { key: "what_next", name: "What next" },
  { key: "scenario_section", name: "Scenario" },
  { key: "impact_section", name: "Impact" },
];

function isSection(value: unknown): value is ExecutiveSection {
  return typeof value === "object" && value !== null && "headline" in value;
}

interface Slide {
  kind: "question" | "section" | "evidence";
  label: string;
  heading: string;
  body?: React.ReactNode;
}

/**
 * Full-screen presentation of one answer: the question, each section in
 * reading order, then the evidence.
 *
 * This is how the product is shown to a room, so it is built as a keynote:
 * one idea per slide, large type, a single figure or chart, and arrow keys to
 * drive it. Slides carry only what the answer already contains.
 */
export function PresentationMode({
  result,
  onClose,
}: {
  result: MultiAgentWorkflowResult;
  onClose: () => void;
}) {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [mounted, setMounted] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const restoreFocus = useRef<Element | null>(null);

  useEffect(() => {
    setMounted(true);
    restoreFocus.current = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    containerRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      if (restoreFocus.current instanceof HTMLElement) restoreFocus.current.focus();
    };
  }, []);

  const slides = useMemo<Slide[]>(() => {
    const out: Slide[] = [
      { kind: "question", label: "The question", heading: result.query },
    ];

    const response = result.management_response;
    const narrativeLead = firstSentence(result.composed_answer);

    if (response) {
      const present = SECTION_ORDER.map(({ key, name }) => ({
        name,
        section: (response as Record<string, unknown>)[key],
      })).filter((e): e is { name: string; section: ExecutiveSection } => isSection(e.section));

      present.forEach(({ name, section }, i) => {
        const heading = isUnusableHeadline(section.headline)
          ? (i === 0 && narrativeLead) ||
            describeResult(result.query_result, result.chart_spec, name)
          : section.headline;

        const { tiles } = splitKpis(section.kpis ?? {});
        const scoped = tiles.slice(0, 3).map((t) => ({
          ...t,
          scope: scopeForValue(t.raw, result.query_result) ?? t.scope ?? null,
        }));

        out.push({
          kind: "section",
          label: name,
          heading,
          body: (
            <div className="space-y-8">
              {i === 0 && result.chart_spec ? (
                <div className="mx-auto w-full max-w-5xl">
                  <PlotlyChartRenderer chartSpec={result.chart_spec} queryResult={result.query_result} />
                </div>
              ) : null}

              {scoped.length > 0 ? (
                <div
                  className={clsx(
                    "mx-auto grid w-full max-w-5xl gap-px overflow-hidden rounded-card",
                    "border border-[var(--border)] bg-[var(--border)]",
                    scoped.length === 1 ? "sm:w-fit" : scoped.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"
                  )}
                >
                  {scoped.map((tile) => (
                    <div key={tile.metricKey} className="bg-surface px-6 py-5">
                      <p className="label-caps">{tile.label}</p>
                      <p className="num-display gold-foil mt-2 text-[clamp(1.75rem,4vw,3rem)] font-bold leading-none">
                        {tile.figure?.display ?? "—"}
                      </p>
                      {tile.scope ? <p className="mt-2 text-label text-faint">{tile.scope}</p> : null}
                    </div>
                  ))}
                </div>
              ) : null}

              {section.disclaimers.length > 0 ? (
                <div className="mx-auto max-w-3xl space-y-2 rounded-card border border-[var(--border)] bg-raised px-5 py-4 text-left">
                  {section.disclaimers.map((d, k) => (
                    <p key={k} className="text-slide-sub text-text">
                      {d}
                    </p>
                  ))}
                </div>
              ) : section.content ? (
                <div className="mx-auto max-w-3xl text-left">
                  <Markdown content={section.content} />
                </div>
              ) : null}
            </div>
          ),
        });
      });
    }

    const queryResult = result.query_result;
    out.push({
      kind: "evidence",
      label: "The evidence",
      heading: result.sanitized_sql ? "Every figure traces to this query" : "How this was produced",
      body: (
        <div className="mx-auto w-full max-w-5xl space-y-5 text-left">
          {result.sanitized_sql ? (
            <pre className="scroll-quiet overflow-x-auto rounded-card border border-[var(--border)] bg-surface px-5 py-4 text-left">
              <code className="font-mono text-[clamp(0.8rem,1.1vw,1rem)] leading-relaxed text-text">
                {result.sanitized_sql}
              </code>
            </pre>
          ) : (
            <p className="text-slide-sub text-muted">
              No SQL was recorded for this run
              {result.specialist_capability
                ? ` — the ${result.specialist_capability.replace(/_/g, " ")} engine produced the figures directly.`
                : "."}
            </p>
          )}

          {queryResult && queryResult.rows.length > 0 ? (
            <DataTable
              columns={queryResult.columns}
              rows={queryResult.rows.slice(0, 8)}
              caption={`${queryResult.row_count} rows returned in ${formatDuration(queryResult.execution_time_ms)}`}
              maxHeight="18rem"
            />
          ) : null}

          {result.verification && result.verification.checks_passed.length > 0 ? (
            <p className="text-slide-sub text-muted">
              Checks passed: {result.verification.checks_passed.join(" · ")}
            </p>
          ) : null}
        </div>
      ),
    });

    return out;
  }, [result]);

  const go = useCallback(
    (delta: number) => {
      setDirection(delta > 0 ? 1 : -1);
      setIndex((i) => Math.min(Math.max(i + delta, 0), slides.length - 1));
    },
    [slides.length]
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      } else if (event.key === "ArrowRight" || event.key === " " || event.key === "PageDown") {
        event.preventDefault();
        go(1);
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        go(-1);
      } else if (event.key === "Home") {
        event.preventDefault();
        setIndex(0);
      } else if (event.key === "End") {
        event.preventDefault();
        setIndex(slides.length - 1);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [go, onClose, slides.length]);

  if (!mounted) return null;

  const slide = slides[index];

  return createPortal(
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-label="Presentation"
      tabIndex={-1}
      className="fixed inset-0 z-[100] flex flex-col bg-ground focus:outline-none"
    >
      <header className="flex items-center justify-between gap-4 border-b border-[var(--border)] px-6 py-3">
        <p className="label-caps font-medium text-accent">{slide.label}</p>
        <div className="flex items-center gap-4">
          <p className="num text-label text-muted" aria-live="polite">
            {index + 1} / {slides.length}
          </p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Exit presentation (Escape)"
            className="flex h-9 w-9 items-center justify-center rounded-control text-muted transition-colors hover:bg-raised hover:text-text"
          >
            <X aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Progress: how far through the answer the room is. */}
      <div className="h-0.5 w-full overflow-hidden bg-[var(--rule)]">
        {/* scaleX rather than width: a composite-only property, so advancing a
            slide never re-lays-out the bar. */}
        <div
          className="h-full w-full origin-left transition-transform duration-300 ease-out motion-reduce:transition-none"
          style={{
            transform: `scaleX(${(index + 1) / slides.length})`,
            backgroundImage: "linear-gradient(90deg, var(--gold-muted), var(--accent))", // taste-skill-ignore: lit along its length by the one light source
          }}
        />
      </div>

      <main className="scroll-quiet flex-1 overflow-y-auto px-6 py-10 sm:px-12">
        <div
          key={index}
          className="mx-auto flex min-h-full w-full max-w-6xl flex-col justify-center gap-8 text-center"
          style={{
            animation: `slide-in 380ms var(--ease-out) both`,
            // The slide enters from the side the reader is travelling towards.
            ["--slide-from" as string]: direction > 0 ? "28px" : "-28px",
          }}
        >
          <h2
            className={clsx(
              "mx-auto max-w-5xl text-balance text-text",
              // The question is the product speaking, so it takes the display
              // face, as it does in the thread. A statement of fact stays in
              // the interface face, where weight carries it.
              slide.kind === "question"
                ? "font-display text-slide"
                : "text-[clamp(1.75rem,4.2vw,3.25rem)] font-bold leading-[1.08]"
            )}
          >
            {slide.heading}
          </h2>
          {slide.body}
        </div>
      </main>

      <footer className="flex items-center justify-between gap-4 border-t border-[var(--border)] px-6 py-3">
        <p className="hidden text-label text-faint sm:block">
          Arrow keys or space to advance · Escape to exit
        </p>
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => go(-1)}
            disabled={index === 0}
            aria-label="Previous slide"
            className="flex h-9 w-9 items-center justify-center rounded-control border border-[var(--control)] text-text transition-colors hover:bg-raised disabled:opacity-35"
          >
            <ChevronLeft aria-hidden="true" className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => go(1)}
            disabled={index === slides.length - 1}
            aria-label="Next slide"
            className="flex h-9 w-9 items-center justify-center rounded-control border border-[var(--control)] text-text transition-colors hover:bg-raised disabled:opacity-35"
          >
            <ChevronRight aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>
      </footer>
    </div>,
    document.body
  );
}

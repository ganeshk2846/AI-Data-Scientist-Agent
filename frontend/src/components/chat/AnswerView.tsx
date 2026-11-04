"use client";

import React, { useCallback, useRef, useState } from "react";
import { MultiAgentWorkflowResult } from "@/types/api";
import { Markdown } from "@/components/ui/Markdown";
import { ManagementResponseView } from "./ManagementResponseView";
import { EvidencePanel, EVIDENCE_SQL_ANCHOR } from "./EvidencePanel";
import { PlotlyChartRenderer } from "@/components/PlotlyChartRenderer";
import { ClarificationPrompt } from "./ClarificationPrompt";
import { RefusalBanner } from "./RefusalBanner";
import { StreamingStepper, StepView } from "./StreamingStepper";
import { PresentationMode } from "./PresentationMode";
import { Presentation } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { formatDuration } from "@/lib/format";
import { isSeriesResult } from "@/lib/narrative";

/** Plain-language names for the specialist pipelines. */
const CAPABILITY_LABEL: Record<string, string> = {
  churn: "churn engine",
  scenario: "scenario engine",
  impact: "impact engine",
  order_drop: "order-drop engine",
};

interface AnswerViewProps {
  result: MultiAgentWorkflowResult;
  onAsk: (question: string) => void;
}

/**
 * One complete answer: the sections, the chart, the findings, the quiet meta
 * line, the follow-ups, and the evidence that backs all of it.
 */
export function AnswerView({ result, onAsk }: AnswerViewProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [openedBy, setOpenedBy] = useState<string | null>(null);
  const [presenting, setPresenting] = useState(false);
  const evidenceRef = useRef<HTMLDivElement>(null);

  /** The provenance link: a figure opens the evidence at what produced it. */
  const revealEvidence = useCallback((figureLabel?: string) => {
    setOpenedBy(figureLabel ?? null);
    setEvidenceOpen(true);
    // Wait for the disclosure to lay out before scrolling to it.
    window.requestAnimationFrame(() => {
      const target = document.getElementById(EVIDENCE_SQL_ANCHOR) ?? evidenceRef.current;
      target?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }, []);

  const analytical = result.analytical_result ?? null;
  const capability = result.specialist_capability
    ? (CAPABILITY_LABEL[result.specialist_capability] ?? result.specialist_capability)
    : null;

  const hasSections =
    result.management_response !== null &&
    result.management_response !== undefined &&
    [
      result.management_response.what,
      result.management_response.why,
      result.management_response.so_what,
      result.management_response.what_next,
      result.management_response.scenario_section,
      result.management_response.impact_section,
    ].some(Boolean);

  const findings = analytical?.findings ?? [];
  const nextSteps = analytical?.recommended_next_steps ?? [];
  /**
   * Only a query that actually ran and matched nothing is an empty result.
   *
   * `verification.empty_result` cannot be used on its own: the specialist
   * pipelines return it as true while also reporting a non-zero row_count and
   * no query_result at all, so trusting it alone prints "No rows matched" over
   * a screen full of figures.
   */
  const emptyResult = Boolean(result.query_result) && result.query_result?.row_count === 0;

  /**
   * A many-row result of one measure is a series: it leads with its chart,
   * because a single tile lifted out of twelve months is not the answer.
   */
  const leadsWithChart = isSeriesResult(result.query_result, result.chart_spec);
  const chartNode = result.chart_spec ? (
    <PlotlyChartRenderer chartSpec={result.chart_spec} queryResult={result.query_result} />
  ) : null;

  // The completed run's steps, with the backend's own durations.
  const steps: StepView[] = result.trace_steps.map((t) => ({
    step: t.step,
    status: t.status,
    message: t.message,
    durationMs: t.duration_ms,
  }));

  return (
    <div className="space-y-10">
      {result.clarification?.needs_clarification ? (
        <ClarificationPrompt clarification={result.clarification} onSelectOption={onAsk} />
      ) : null}

      {!result.answerability.is_answerable ? (
        <RefusalBanner answerability={result.answerability} onSelectAlternative={onAsk} />
      ) : null}

      {emptyResult ? (
        <section className="plane-raised p-6">
          <h3 className="text-headline font-semibold text-text">No rows matched</h3>
          <p className="mt-1 text-body text-text">
            The query ran successfully against{" "}
            {result.selected_tables.length > 0 ? result.selected_tables.join(", ") : "the connected data"} and
            returned nothing. The window asked for has no records.
          </p>
        </section>
      ) : null}

      {/* The structured answer, or the narrative when no sections were composed. */}
      {hasSections && result.management_response ? (
        <ManagementResponseView
          result={result}
          onRevealEvidence={revealEvidence}
          evidenceLabel={capability ? `${capability} output` : "SQL"}
          chart={leadsWithChart ? chartNode : undefined}
        />
      ) : (
        <>
          {leadsWithChart ? <div className="arrive">{chartNode}</div> : null}
          {result.composed_answer ? (
            <Markdown content={result.composed_answer} className="arrive max-w-prose-measure" />
          ) : null}
        </>
      )}

      {/* The narrative, when sections are present and say something different. */}
      {hasSections && result.composed_answer && result.management_response?.composed_markdown !== result.composed_answer ? (
        <details className="group">
          <summary className="cursor-pointer list-none text-label text-muted hover:text-text">
            <span className="link-gold">Read the full narrative</span>
          </summary>
          <Markdown content={result.composed_answer} className="mt-3 max-w-prose-measure" />
        </details>
      ) : null}

      {chartNode && !leadsWithChart ? <div className="arrive">{chartNode}</div> : null}

      {findings.length > 0 ? (
        <section className="space-y-2">
          <h3 className="text-headline font-semibold text-text">Findings</h3>
          <ul className="max-w-prose-measure space-y-1.5 text-body text-text">
            {findings.map((f, i) => (
              <li key={i} className="flex gap-2.5">
                <span aria-hidden="true" className="mt-[0.6em] h-1 w-1 shrink-0 rounded-full bg-[var(--control)]" />
                <span className="min-w-0 flex-1">{f}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {nextSteps.length > 0 ? (
        <section className="space-y-2">
          <h3 className="text-headline font-semibold text-text">Recommended next steps</h3>
          <ol className="max-w-prose-measure space-y-1.5 text-body text-text">
            {nextSteps.map((s, i) => (
              <li key={i} className="flex gap-2.5">
                <span className="num mt-px w-4 shrink-0 text-right text-label text-muted">{i + 1}.</span>
                <span className="min-w-0 flex-1">{s}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {/* How it was answered — the real execution record, with real timings. */}
      <StreamingStepper steps={steps} live={false} totalMs={result.total_duration_ms} />

      <div ref={evidenceRef}>
        <EvidencePanel result={result} open={evidenceOpen} onOpenChange={setEvidenceOpen} openedBy={openedBy} />
      </div>

      {/* Secondary, quieter: one meta line, grey, no pills. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-label text-muted">
        {capability ? <span>Answered by the {capability}</span> : <span>Answered by the SQL pipeline</span>}
        <span aria-hidden="true">·</span>
        <span>
          {result.route.intent} intent, {Math.round(result.route.confidence * 100)}% confidence
        </span>
        <span aria-hidden="true">·</span>
        <span className="num">{formatDuration(result.total_duration_ms)} total</span>
        {result.query_result ? (
          <>
            <span aria-hidden="true">·</span>
            <span className="num">{formatDuration(result.query_result.execution_time_ms)} in the database</span>
          </>
        ) : null}
      </p>

        <Button
          size="sm"
          variant="secondary"
          icon={<Presentation className="h-3.5 w-3.5" />}
          onClick={() => setPresenting(true)}
        >
          Present
        </Button>
      </div>

      {presenting ? <PresentationMode result={result} onClose={() => setPresenting(false)} /> : null}

      {result.suggested_followups.length > 0 ? (
        <section className="space-y-2 border-t border-[var(--rule)] pt-4">
          <h3 className="label-caps">Ask next</h3>
          <ul className="flex flex-wrap gap-2">
            {result.suggested_followups.map((q) => (
              <li key={q}>
                <button
                  type="button"
                  onClick={() => onAsk(q)}
                  className={[
                    "responds rounded-control border border-[var(--border)] bg-surface px-3.5 py-2",
                    "text-left text-body text-text shadow-raised",
                  ].join(" ")}
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

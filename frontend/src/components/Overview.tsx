"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import { ArrowRight } from "lucide-react";
import {
  fetchReadiness,
  fetchSchemaStatus,
  fetchObservabilityMetrics,
  executeChatQuery,
} from "@/lib/api";
import { StatGroup, StatItem } from "@/components/ui/Stat";
import { Notice } from "@/components/ui/Notice";
import { Button } from "@/components/ui/Button";
import { PlotlyChartRenderer } from "@/components/PlotlyChartRenderer";
import { formatFigure, formatDuration, databaseName, humanizeKey } from "@/lib/format";
import { formatPeriodLabel, periodRange } from "@/lib/narrative";
import { useTilt } from "@/lib/useTilt";
import { readOpeningAnswer, writeOpeningAnswer } from "@/lib/openingAnswer";
import { Hero } from "@/components/hero/Hero";

/**
 * The question the landing view answers with, so the screen is alive before
 * anyone types. It is a real query against the connected warehouse — its
 * figures and its chart are the backend's, not a mock.
 */
const OVERVIEW_QUESTION = "What was total revenue by month in 2025?";

export const SUGGESTED_QUESTIONS = [
  {
    text: "What was total revenue by month in 2025?",
    note: "A series over time, drawn as a chart",
  },
  {
    text: "What are the top 5 product categories by revenue?",
    note: "A ranking, with the rows behind it",
  },
  {
    text: "Which customer segments are at risk of churn and what revenue is at risk?",
    note: "Runs the churn engine, with its limits stated",
  },
  {
    text: "How many customers belong to each customer segment?",
    note: "A breakdown across the customer base",
  },
] as const;

function SuggestionCard({ text, note, onAsk }: { text: string; note: string; onAsk: (q: string) => void }) {
  const tilt = useTilt(2.5);
  return (
    <button
      type="button"
      onClick={() => onAsk(text)}
      onPointerMove={tilt.onPointerMove}
      onPointerLeave={tilt.onPointerLeave}
      className={clsx(
        "tilt tilt-sheen responds group relative h-full w-full overflow-hidden",
        "plane-raised p-5 text-left"
      )}
    >
      <span className="block text-[15px] font-medium leading-snug text-text">{text}</span>
      <span className="mt-2 flex items-center gap-1.5 text-label text-muted">
        {note}
        <ArrowRight
          aria-hidden="true"
          className="h-3 w-3 transition-transform duration-200 ease-out group-hover:translate-x-0.5 motion-reduce:transition-none"
        />
      </span>
    </button>
  );
}

function StatSkeleton() {
  return (
    <div className="grid gap-px overflow-hidden rounded-card border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2 lg:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="bg-surface px-4 py-3.5">
          <span className="skeleton block h-[12px] w-20" />
          <span className="skeleton mt-3 block h-[30px] w-28" />
          <span className="skeleton mt-2.5 block h-[11px] w-16" />
        </div>
      ))}
    </div>
  );
}

interface OverviewProps {
  onAsk: (question: string) => void;
}

/**
 * The landing view: what is connected, what the warehouse holds, and one real
 * answer already on screen — so the product looks like it is working before a
 * question is asked.
 *
 * Every figure comes from the API. Nothing on this screen is invented, and no
 * total is derived here: the overview query's own result supplies its figures.
 */
export function Overview({ onAsk }: OverviewProps) {
  const { data: readiness } = useQuery({ queryKey: ["readiness"], queryFn: fetchReadiness });
  const { data: schema } = useQuery({ queryKey: ["schemaStatus"], queryFn: fetchSchemaStatus });
  const { data: metrics } = useQuery({
    queryKey: ["observabilityMetrics"],
    queryFn: () => fetchObservabilityMetrics(),
  });

  // One real query, run once and held across reloads — the landing view shows
  // a live answer without spending a model call every time the page opens.
  const cached = React.useMemo(() => readOpeningAnswer(OVERVIEW_QUESTION), []);
  const {
    data: overview,
    isLoading: overviewLoading,
    isError: overviewFailed,
    error: overviewError,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ["overviewAnswer"],
    queryFn: async () => {
      const result = await executeChatQuery(OVERVIEW_QUESTION, "overview_panel");
      writeOpeningAnswer(OVERVIEW_QUESTION, result);
      return result;
    },
    initialData: cached?.result,
    initialDataUpdatedAt: cached?.savedAt,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    retry: 1,
  });

  const summary = schema?.catalog_summary;
  // Named in real values: what is connected, what it holds, how it is held.
  const scopeLine = [
    databaseName(readiness?.database.path),
    summary ? `${summary.total_tables} tables` : null,
    readiness?.database.read_only_verified ? "read-only, verified" : null,
    readiness?.llm?.model ?? null,
  ]
    .filter(Boolean)
    .join("  ·  ");
  const overviewRows = overview?.query_result ?? null;
  const covered = periodRange(overviewRows);

  /** Headline figures: the warehouse's shape, then the overview answer's own. */
  const tiles: StatItem[] = [];

  if (summary) {
    tiles.push({
      metricKey: "total_rows",
      raw: summary.total_rows,
      label: "Rows in the warehouse",
      figure: formatFigure(summary.total_rows, "total_rows"),
      scope: databaseName(readiness?.database.path) ?? null,
    });
    tiles.push({
      metricKey: "total_tables",
      raw: summary.total_tables,
      label: "Tables catalogued",
      figure: formatFigure(summary.total_tables, "total_tables"),
      scope: covered ? `Covering ${covered}` : "Schema prepared",
    });
  }

  // Figures the overview query itself returned, labelled by its own columns.
  if (overviewRows && overviewRows.rows.length > 0) {
    const numericColumns = overviewRows.columns.filter((c) =>
      overviewRows.rows.every((r) => typeof r[c] === "number")
    );
    for (const column of numericColumns.slice(0, 1)) {
      const latest = overviewRows.rows[overviewRows.rows.length - 1];
      const value = latest[column];
      if (typeof value !== "number") continue;
      const scopeColumn = overviewRows.columns.find((c) => typeof latest[c] === "string");
      tiles.push({
        metricKey: column,
        raw: value,
        label: humanizeKey(column),
        figure: formatFigure(value, column),
        // The row's own scope, said as a reader would say it: a tile that
        // holds one month must not read as if it held the year.
        scope: scopeColumn
          ? formatPeriodLabel(String(latest[scopeColumn])) ?? String(latest[scopeColumn])
          : null,
      });
    }
  }

  if (metrics) {
    tiles.push({
      metricKey: "total_runs",
      raw: metrics.total_runs,
      label: "Questions answered",
      figure: formatFigure(metrics.total_runs, "total_runs"),
      scope: `Typically ${formatDuration(metrics.latency_p50_ms)}`,
    });
  }

  return (
    <div className="space-y-14">
      <Hero
        queryResult={overviewRows}
        chartSpec={overview?.chart_spec}
        sql={overview?.sanitized_sql}
        title="Every figure, proven."
        subtitle="Ask a business question in plain language. The answer arrives with its uncertainty, its rows, and the SQL that produced every number."
        scope={scopeLine}
        state={overviewFailed ? "error" : "loading"}
        errorMessage={overviewError instanceof Error ? overviewError.message : null}
        onRetry={() => refetchOverview()}
      />

      <section aria-label="What is connected" className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-headline font-semibold text-text">The warehouse</h2>
          {readiness?.database.read_only_verified ? (
            <p className="text-label text-muted">
              Read-only access, verified. The agent can never write to it.
            </p>
          ) : null}
        </div>
        {tiles.length === 0 ? <StatSkeleton /> : <StatGroup items={tiles} />}
      </section>

      {overviewLoading ? (
        <section aria-label="Loading an opening answer" className="space-y-4">
          <h2 className="text-headline font-semibold text-text">An answer to start from</h2>
          <div className="plane-raised p-5">
            <span className="skeleton block h-[14px] w-52" />
            <span className="skeleton mt-2 block h-[11px] w-36" />
            <span className="skeleton mt-4 block h-[200px] w-full" />
          </div>
        </section>
      ) : overview?.chart_spec ? (
        <section aria-label="An answer to start from" className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-headline font-semibold text-text">An answer to start from</h2>
            <button type="button" onClick={() => onAsk(OVERVIEW_QUESTION)} className="link-gold text-label">
              Ask this again in full
            </button>
          </div>
          <PlotlyChartRenderer chartSpec={overview.chart_spec} queryResult={overview.query_result} headingLevel={3} />
        </section>
      ) : overviewFailed ? (
        /* A failed opening query says so and offers to run again, rather than
           leaving a grey panel that looks like a chart that never arrived. */
        <section aria-label="An answer to start from" className="space-y-4">
          <h2 className="text-headline font-semibold text-text">An answer to start from</h2>
          <Notice
            tone="warning"
            title="The opening query did not run"
            action={
              <Button size="sm" variant="secondary" onClick={() => refetchOverview()}>
                Run it again
              </Button>
            }
          >
            {overviewError instanceof Error
              ? overviewError.message
              : "The agent could not be reached. Everything else on this screen is live."}
          </Notice>
        </section>
      ) : null}

      <section aria-label="Suggested questions" className="space-y-4">
        <h2 className="text-headline font-semibold text-text">Or ask one of these</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <li key={q.text}>
              <SuggestionCard text={q.text} note={q.note} onAsk={onAsk} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

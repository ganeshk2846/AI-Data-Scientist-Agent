"use client";

import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import { fetchObservabilityMetrics, fetchRecentTraces, fetchRunSpans } from "@/lib/api";
import { StageSpanRecord } from "@/types/api";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { StatGroup, StatItem } from "./ui/Stat";
import { Disclosure } from "./ui/Disclosure";
import { SqlBlock } from "./ui/SqlBlock";
import { formatDuration, formatFigure } from "@/lib/format";
import { ScreenHeader } from "./ui/ScreenHeader";

/** The spans for one run, fetched only when its row is opened. */
function RunSpans({ runId }: { runId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["runSpans", runId],
    queryFn: () => fetchRunSpans(runId),
  });

  if (isLoading) {
    return (
      <ul className="space-y-1.5" aria-label="Loading stage spans">
        {[0, 1, 2].map((i) => (
          <li key={i} className="skeleton h-[18px] w-full" />
        ))}
      </ul>
    );
  }

  const spans = (data ?? []) as StageSpanRecord[];
  if (spans.length === 0) {
    return <p className="text-body text-muted">No stage spans were recorded for this run.</p>;
  }

  const longest = Math.max(...spans.map((s) => s.duration_ms), 1);

  return (
    <ol className="space-y-1.5">
      {spans.map((span) => (
        <li key={span.span_id} className="space-y-1">
          <div className="flex items-baseline justify-between gap-3">
            <span className="min-w-0 truncate text-body text-text">{span.stage_name.replace(/_/g, " ")}</span>
            <span className="num shrink-0 text-label text-muted">{formatDuration(span.duration_ms)}</span>
          </div>
          {/* A proportional bar: thin and grey, since it is not the screen's main series. */}
          <div className="h-[3px] w-full rounded-full bg-[var(--rule)]">
            <div
              className="h-full rounded-full bg-[var(--control)]"
              style={{ width: `${Math.max((span.duration_ms / longest) * 100, 1)}%` }}
            />
          </div>
        </li>
      ))}
    </ol>
  );
}

/**
 * Telemetry: how the agent is performing across runs, and what each run did.
 *
 * Latency percentiles are the screen's question, so they lead. Every figure is
 * the backend's; nothing is averaged or re-derived here.
 */
export function ObservabilityDashboard() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "verified" | "failed">("all");
  const [allStages, setAllStages] = useState(false);

  const { data: metrics, isLoading: loadingMetrics, refetch: refetchMetrics } = useQuery({
    queryKey: ["observabilityMetrics"],
    queryFn: () => fetchObservabilityMetrics(),
    refetchInterval: 30_000,
  });

  const { data: traces, isLoading: loadingTraces, refetch: refetchTraces } = useQuery({
    queryKey: ["recentTraces"],
    queryFn: () => fetchRecentTraces(50),
    refetchInterval: 30_000,
  });

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return (traces ?? []).filter((trace) => {
      if (term) {
        const haystack = `${trace.query} ${trace.intent} ${trace.sql_executed ?? ""}`.toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      if (statusFilter === "all") return true;
      const verified = trace.verification_status.toLowerCase().includes("verified");
      return statusFilter === "verified" ? verified : !verified;
    });
  }, [traces, search, statusFilter]);

  const tiles: StatItem[] = metrics
    ? [
        {
          metricKey: "latency_p50_ms",
          label: "Median latency",
          figure: { display: formatDuration(metrics.latency_p50_ms), exact: `${metrics.latency_p50_ms} ms`, abbreviated: false, unit: null },
          scope: metrics.window === "all" ? "All recorded runs" : metrics.window,
        },
        {
          metricKey: "latency_p95_ms",
          label: "95th percentile",
          figure: { display: formatDuration(metrics.latency_p95_ms), exact: `${metrics.latency_p95_ms} ms`, abbreviated: false, unit: null },
        },
        {
          metricKey: "total_runs",
          label: "Runs",
          figure: formatFigure(metrics.total_runs, "total_runs"),
        },
        {
          metricKey: "success_rate_pct",
          label: "Success rate",
          figure: formatFigure(metrics.success_rate_pct, "success_rate_pct"),
        },
      ]
    : [];

  return (
    <div className="space-y-10">
      <ScreenHeader
        title="Activity"
        description={
          metrics
            ? `Every question the agent has answered on ${metrics.active_engine}: how long it took, which stage it spent the time in, and whether the answer verified.`
            : "Every question the agent has answered: latency, stages and verification."
        }
        actions={
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              refetchMetrics();
              refetchTraces();
            }}
          >
            Refresh
          </Button>
        }
      />

      {loadingMetrics ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="plane-raised px-5 py-5">
              <span className="skeleton block h-[11px] w-24" />
              <span className="skeleton mt-3 block h-[38px] w-32" />
            </div>
          ))}
        </div>
      ) : tiles.length > 0 ? (
        <StatGroup items={tiles} />
      ) : (
        <p className="rounded-card border border-dashed border-[var(--border)] px-3 py-6 text-center text-body text-muted">
          No telemetry has been recorded yet. Ask a question and it will appear here.
        </p>
      )}

      {metrics && Object.keys(metrics.stage_latencies).length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-headline font-semibold text-text">Where the time goes</h2>
          <ol className="plane-raised divide-y divide-[var(--rule)] overflow-hidden">
            {Object.entries(metrics.stage_latencies)
              .sort((a, b) => b[1].p50_ms - a[1].p50_ms)
              .slice(0, allStages ? undefined : 6)
              .map(([stage, stat]) => (
                <li key={stage} className="row-responds flex items-baseline justify-between gap-4 px-4 py-3">
                  <span className="min-w-0 truncate text-body text-text">{stage.replace(/_/g, " ")}</span>
                  <span className="shrink-0 text-right">
                    <span className="num text-body text-text">{formatDuration(stat.p50_ms)}</span>
                    <span className="num ml-3 text-label text-muted">p95 {formatDuration(stat.p95_ms)}</span>
                  </span>
                </li>
              ))}
          </ol>
          {Object.keys(metrics.stage_latencies).length > 6 ? (
            <button
              type="button"
              onClick={() => setAllStages((v) => !v)}
              className="link-gold text-label"
            >
              {allStages
                ? "Show the slowest 6"
                : `Show all ${Object.keys(metrics.stage_latencies).length} stages`}
            </button>
          ) : null}
        </section>
      ) : null}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-headline font-semibold text-text">
            Recent runs
            <span className="ml-2 font-normal text-label text-muted">
              {filtered.length} of {traces?.length ?? 0}
            </span>
          </h2>

          {/* The search grows and the filters wrap, so the row never pushes a
              control past the canvas edge on a phone. */}
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <label htmlFor="trace-search" className="sr-only">
              Search runs
            </label>
            <input
              id="trace-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search questions and SQL"
              className="h-8 min-w-0 flex-1 rounded-control border border-[var(--control)] bg-surface px-2.5 text-body text-text placeholder:text-faint focus:border-[var(--text)] focus:outline-none sm:w-56 sm:flex-none"
            />
            <div role="group" aria-label="Filter by verification" className="flex shrink-0 items-center gap-0.5 rounded-control border border-[var(--border)] p-0.5">
              {(["all", "verified", "failed"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={statusFilter === value}
                  onClick={() => setStatusFilter(value)}
                  className={clsx(
                    "h-7 rounded-[4px] px-2.5 text-label capitalize",
                    "transition-[background-color,color] duration-[90ms] ease-out",
                    statusFilter === value
                      ? "bg-active font-medium text-text"
                      : "text-muted hover:[@media(hover:hover)and(pointer:fine)]:text-accent"
                  )}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loadingTraces ? (
          <ul className="space-y-1.5" aria-label="Loading runs">
            {[0, 1, 2, 3, 4].map((i) => (
              <li key={i} className="rounded-card border border-[var(--border)] px-3.5 py-3">
                <span className="skeleton block h-[14px] w-2/3" />
                <span className="skeleton mt-2 block h-[12px] w-1/3" />
              </li>
            ))}
          </ul>
        ) : filtered.length === 0 ? (
          <p className="rounded-card border border-dashed border-[var(--border)] px-3 py-8 text-center text-body text-muted">
            {traces && traces.length > 0
              ? "No runs match this filter."
              : "No runs recorded yet."}
          </p>
        ) : (
          <ul className="space-y-1.5">
            {filtered.map((trace) => {
              const verified = trace.verification_status.toLowerCase().includes("verified");
              return (
                <li key={trace.run_id} className="rounded-card border border-[var(--border)] bg-surface px-3.5">
                  <Disclosure
                    label={<span className="block truncate text-body font-normal text-text">{trace.query}</span>}
                    meta={
                      <span className="flex items-center gap-2">
                        <Badge variant={verified ? "positive" : "negative"}>
                          {verified ? "Verified" : trace.verification_status}
                        </Badge>
                        <span className="num">{formatDuration(trace.latency_ms)}</span>
                      </span>
                    }
                  >
                    <div className="space-y-3 pb-3">
                      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-4">
                        {[
                          { label: "Intent", value: trace.intent },
                          { label: "Rows", value: String(trace.row_count) },
                          { label: "LLM calls", value: String(trace.llm_calls_count ?? 0) },
                          { label: "When", value: new Date(trace.created_at).toLocaleString() },
                        ].map((e) => (
                          <div key={e.label}>
                            <dt className="text-label text-muted">{e.label}</dt>
                            <dd className="num text-body text-text">{e.value}</dd>
                          </div>
                        ))}
                      </dl>

                      {trace.error_class ? (
                        <p className="text-body text-negative">Error class: {trace.error_class}</p>
                      ) : null}

                      {trace.sql_executed ? (
                        <SqlBlock sql={trace.sql_executed} label="SQL for this run" />
                      ) : (
                        <p className="text-body text-muted">No SQL was recorded for this run.</p>
                      )}

                      <div className="space-y-1.5">
                        <p className="text-label font-medium text-text">Stage spans</p>
                        <RunSpans runId={trace.run_id} />
                      </div>
                    </div>
                  </Disclosure>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

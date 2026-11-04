"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
import { ChartSpecification, QueryExecutionResult } from "@/types/api";
import { DataTable } from "@/components/ui/DataTable";
import { useTheme, readToken, readTokenRgba } from "@/lib/useTheme";
import { useChartParallax } from "@/lib/useChartParallax";
import { formatPeriodLabel } from "@/lib/narrative";

/**
 * The backend writes its alt text with the raw keys it queried on
 * ("from 2025-01 to 2025-12"). A period is said the way a reader says it
 * everywhere else on the screen, so it is said that way here too. Only the
 * rendering of the date changes; no value does.
 */
function humanisePeriods(text: string): string {
  return text.replace(/\d{4}-\d{2}(-\d{2})?/g, (match) => formatPeriodLabel(match) ?? match);
}

interface PlotlyChartRendererProps {
  chartSpec: ChartSpecification;
  queryResult?: QueryExecutionResult | null;
  /**
   * The chart's caption is a real heading, so it has to nest under whatever
   * heading precedes it: h3 under a section's h2, h4 under an h3.
   */
  headingLevel?: 3 | 4;
}

type PlotlyTrace = Record<string, unknown>;

/**
 * Renders a backend chart spec with the project's own palette.
 *
 * The backend ships presentation decisions inside `plotly_layout` and
 * `plotly_data` that this product cannot use: an indigo series (a banned hue
 * here) and axis/font colours fixed for a dark background, which are
 * unreadable in light mode. This component replaces every colour with a token
 * read from the live theme and re-renders when the theme changes.
 *
 * It never touches x/y values, counts, ordering or labels. Colour and chrome
 * are presentation; the data is the backend's.
 */
export function PlotlyChartRenderer({ chartSpec, queryResult, headingLevel = 4 }: PlotlyChartRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const forcedTable = chartSpec.fallback_to_table || chartSpec.chart_type === "table";
  const [viewMode, setViewMode] = useState<"chart" | "table">(forcedTable ? "table" : "chart");
  const [renderError, setRenderError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(!forcedTable);

  const seriesCount = (chartSpec.plotly_data ?? []).length;

  /** Re-colours a trace in place of whatever the backend chose. */
  const themeTrace = useCallback(
    (trace: PlotlyTrace, index: number): PlotlyTrace => {
      // One series has no adjacency to separate, so it takes the accent gold
      // itself; several series take the validated four-slot ramp.
      const slots =
        seriesCount <= 1
          ? [readToken("--chart-primary", "#9a7b1e")]
          : [
              readToken("--series-1", "#9a7b1e"),
              readToken("--series-2", "#1d5fbf"),
              readToken("--series-3", "#8c2f10"),
              readToken("--series-4", "#0b6ea8"),
            ];
      // A fifth series and beyond folds to neutral rather than inventing a hue.
      const colour = index < slots.length ? slots[index] : readToken("--series-other", "#8a8a8a");
      const next: PlotlyTrace = { ...trace };

      const existingLine = (trace.line ?? {}) as Record<string, unknown>;
      const existingMarker = (trace.marker ?? {}) as Record<string, unknown>;

      next.line = { ...existingLine, color: colour, width: seriesCount <= 1 ? 2.5 : 2, shape: "linear" };
      next.marker = { ...existingMarker, color: colour, line: { width: 0 } };

      // No point markers on a line: the study's lines carry none.
      if (trace.type === "scatter" && typeof trace.mode === "string" && trace.mode.includes("markers")) {
        next.mode = seriesCount > 1 || chartSpec.chart_type === "scatter" ? trace.mode : "lines";
      }
      if (trace.type === "pie") {
        next.marker = { colors: slots, line: { color: readToken("--surface", "#ffffff"), width: 2 } };
      }
      // Depth under the line: a shallow fill in the series' own colour, so
      // the curve sits on a surface rather than floating on the grid.
      if (trace.type === "scatter" && seriesCount <= 1 && chartSpec.chart_type === "line") {
        next.fill = "tozeroy";
        next.fillcolor = readTokenRgba("--chart-primary", 0.14, "#9a7b1e");
      } else if ("fill" in next) {
        next.fill = "none";
      }
      return next;
    },
    [chartSpec.chart_type, seriesCount]
  );

  useEffect(() => {
    if (forcedTable || viewMode !== "chart") {
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    const node = containerRef.current;
    let cleanupResize: (() => void) | null = null;
    // Keep the module so cleanup can purge without a second dynamic import.
    let plotly: typeof import("plotly.js-dist-min").default | null = null;

    (async () => {
      try {
        setIsLoading(true);
        setRenderError(null);

        // Lazy: plotly is only fetched when a chart is actually shown.
        plotly = (await import("plotly.js-dist-min")).default;
        if (cancelled || !node) return;

        const ink = readToken("--chart-ink", "#141414");
        const muted = readToken("--muted", "#6b6b6b");
        const grid = readToken("--grid", "#e5e5e5");

        const axis = {
          gridcolor: grid,
          zerolinecolor: grid,
          linecolor: grid,
          tickfont: { color: muted, size: 11 },
          titlefont: { color: muted, size: 11 },
          showline: false,
          automargin: true,
        };

        const data = (chartSpec.plotly_data ?? []).map(themeTrace);

        const firstX = (chartSpec.plotly_data ?? [])[0]?.x;
        const categoricalX =
          Array.isArray(firstX) && firstX.length > 0 && firstX.every((v) => typeof v === "string");

        // Period keys get human tick labels, shortened when there are many of
        // them so the axis never rotates its text.
        const periodTicks = (() => {
          if (!categoricalX) return null;
          const values = firstX as string[];
          const labels = values.map((v) => formatPeriodLabel(v));
          if (labels.some((l) => l === null)) return null;
          const compact = values.length > 6;
          return {
            values,
            text: labels.map((l, i) => {
              const label = l as string;
              if (!compact) return label;
              // "January 2025" becomes "Jan", with the year kept on the first
              // tick and wherever it changes.
              const [month, year] = label.split(" ");
              if (!year) return label;
              const short = month.slice(0, 3);
              const previousYear = i > 0 ? (labels[i - 1] as string).split(" ")[1] : null;
              return previousYear === year ? short : `${short} ${year}`;
            }),
          };
        })();

        // The card's caption already names the chart and its measure, so the
        // backend's in-plot title and axis titles are dropped rather than
        // printed twice. Axis chrome is what the study trims first.
        const { title: _title, ...backendLayout } = (chartSpec.plotly_layout ?? {}) as Record<string, unknown>;
        const stripTitle = (axis: unknown): Record<string, unknown> => {
          const { title: _axisTitle, ...rest } = (axis ?? {}) as Record<string, unknown>;
          return rest;
        };

        const layout = {
          ...backendLayout,
          title: undefined,
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { family: "Geist, Inter, system-ui, sans-serif", color: ink, size: 12 },
          margin: { l: 58, r: 30, t: 10, b: 38 },
          autosize: true,
          // A single series needs no legend; the card title names it.
          showlegend: seriesCount > 1,
          legend: { orientation: "h" as const, y: -0.22, font: { color: muted, size: 11 } },
          hoverlabel: {
            bgcolor: readToken("--surface", "#ffffff"),
            bordercolor: readToken("--border", "#e6e6e6"),
            font: { color: ink, size: 12 },
          },
          xaxis: {
            ...stripTitle(backendLayout.xaxis),
            ...axis,
            // The backend sends categories as strings; left to infer, Plotly
            // reads "2022" as a number and invents 2,022.5 ticks.
            ...(categoricalX ? { type: "category" as const } : {}),
            // `2025-01` is a key, not a label. The tick text is replaced with
            // the period said as a reader would say it; the category values
            // themselves — and so the ordering and the hover — are untouched.
            ...(categoricalX && periodTicks
              ? { tickmode: "array" as const, tickvals: periodTicks.values, ticktext: periodTicks.text }
              : {}),
          },
          yaxis: { ...stripTitle(backendLayout.yaxis), ...axis, nticks: 5 },
        };

        await plotly.newPlot(node, data, layout, {
          responsive: true,
          displayModeBar: false,
          // The chart is decorative-free; the table view is the accessible route.
          staticPlot: false,
        });
        if (cancelled) return;
        setIsLoading(false);

        const onResize = () => {
          if (node && plotly) plotly.Plots.resize(node);
        };
        window.addEventListener("resize", onResize);
        cleanupResize = () => window.removeEventListener("resize", onResize);
      } catch (err: unknown) {
        console.error("Plotly render error:", err);
        if (cancelled) return;
        setRenderError(err instanceof Error ? err.message : "The chart could not be drawn.");
        setViewMode("table");
        setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      // The previous implementation returned this cleanup from inside the async
      // function, so it was never called and every chart leaked a listener.
      if (cleanupResize) cleanupResize();
      if (node && plotly) plotly.purge(node);
    };
  }, [chartSpec, viewMode, forcedTable, themeTrace, seriesCount, theme]);

  const Heading = (headingLevel === 3 ? "h3" : "h4") as "h3" | "h4";
  const parallax = useChartParallax(containerRef);
  const rows = queryResult?.rows ?? [];
  const columns = queryResult?.columns ?? [];

  return (
    <figure className="overflow-hidden rounded-card border border-[var(--border)] bg-surface shadow-raised">
      <figcaption className="flex flex-wrap items-start justify-between gap-2 border-b border-[var(--rule)] px-4 py-3">
        <div className="min-w-0">
          <Heading className="text-section font-semibold text-text">{chartSpec.title}</Heading>
          {chartSpec.subtitle ? <p className="mt-0.5 text-label text-muted">{chartSpec.subtitle}</p> : null}
        </div>

        {!forcedTable && columns.length > 0 ? (
          <div role="group" aria-label="Chart view" className="flex shrink-0 items-center gap-0.5 rounded-control border border-[var(--border)] p-0.5">
            {(["chart", "table"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={viewMode === mode}
                onClick={() => setViewMode(mode)}
                className={clsx(
                  "h-6 rounded-[4px] px-2.5 text-label capitalize transition-colors duration-[120ms]",
                  viewMode === mode ? "bg-active font-medium text-text" : "text-muted"
                )}
              >
                {mode}
              </button>
            ))}
          </div>
        ) : null}
      </figcaption>

      {renderError ? (
        <p className="border-b border-[var(--rule)] px-4 py-2 text-label text-muted">
          The chart could not be drawn, so the rows are shown instead. {renderError}
        </p>
      ) : null}

      {viewMode === "chart" && !forcedTable ? (
        <div
          className="px-2 pb-2 pt-3"
          onPointerMove={parallax.onPointerMove}
          onPointerLeave={parallax.onPointerLeave}
        >
          <div className="relative">
            {/* Opaque and above the plot, so a part-drawn chart is never seen
                through it; it fades rather than popping. */}
            <div
              aria-hidden={!isLoading}
              className={clsx(
                "pointer-events-none absolute inset-0 z-10 rounded-card bg-surface p-2",
                "transition-opacity duration-300 ease-out motion-reduce:transition-none",
                isLoading ? "opacity-100" : "opacity-0"
              )}
            >
              <span className="skeleton block h-full w-full" />
              {isLoading ? <span className="sr-only">Drawing chart</span> : null}
            </div>
            <div
              ref={containerRef}
              role="img"
              aria-label={chartSpec.alt_text ? humanisePeriods(chartSpec.alt_text) : chartSpec.title}
              className={clsx(
                "h-[220px] w-full sm:h-[280px]",
                !isLoading && (chartSpec.chart_type === "bar" ? "chart-rise" : "chart-draw")
              )}
            />
          </div>
          {chartSpec.alt_text ? (
            <p className="px-2 pb-1 pt-2 text-label text-muted">{humanisePeriods(chartSpec.alt_text)}</p>
          ) : null}
        </div>
      ) : (
        <div className="p-4">
          <DataTable
            columns={columns}
            rows={rows}
            truncated={queryResult?.truncated ?? false}
            caption={
              columns.length > 0
                ? `${queryResult?.row_count ?? rows.length} rows — the same values the chart is drawn from`
                : undefined
            }
            emptyMessage="The query returned no rows, so there is nothing to plot."
          />
        </div>
      )}
    </figure>
  );
}

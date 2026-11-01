"use client";

import { useEffect, useRef, useState } from "react";
import { ChartSpecification, QueryExecutionResult } from "@/types/api";
import { BarChart2, Download, Eye, Table as TableIcon } from "lucide-react";

interface PlotlyChartRendererProps {
  chartSpec: ChartSpecification;
  queryResult?: QueryExecutionResult | null;
}

export function PlotlyChartRenderer({ chartSpec, queryResult }: PlotlyChartRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewMode, setViewMode] = useState<"chart" | "table">(
    chartSpec.fallback_to_table ? "table" : "chart"
  );
  const [renderError, setRenderError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(!chartSpec.fallback_to_table);

  useEffect(() => {
    if (chartSpec.fallback_to_table || viewMode !== "chart") {
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    let plotlyInstance: any = null;

    const renderPlot = async () => {
      try {
        setIsLoading(true);
        setRenderError(null);

        // Dynamically import Plotly in browser environment only
        const Plotly = (await import("plotly.js-dist-min")).default;
        plotlyInstance = Plotly;

        if (!isMounted || !containerRef.current) return;

        const data = chartSpec.plotly_data || [];
        const layout = {
          ...chartSpec.plotly_layout,
          autosize: true,
          responsive: true,
        };

        const config = {
          responsive: true,
          displayModeBar: false, // clean minimal aesthetic
        };

        await Plotly.newPlot(containerRef.current, data, layout, config);
        setIsLoading(false);

        const handleResize = () => {
          if (containerRef.current && plotlyInstance) {
            plotlyInstance.Plots.resize(containerRef.current);
          }
        };

        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
      } catch (err: any) {
        console.error("Plotly render error:", err);
        if (isMounted) {
          setRenderError(err.message || "Failed to render Plotly chart.");
          setViewMode("table"); // Graceful fallback to table
          setIsLoading(false);
        }
      }
    };

    renderPlot();

    return () => {
      isMounted = false;
      if (containerRef.current && plotlyInstance) {
        plotlyInstance.purge(containerRef.current);
      }
    };
  }, [chartSpec, viewMode]);

  const handleDownload = async () => {
    try {
      const Plotly = (await import("plotly.js-dist-min")).default;
      if (containerRef.current) {
        await Plotly.downloadImage(containerRef.current, {
          format: "png",
          filename: `${chartSpec.title.toLowerCase().replace(/\s+/g, "_")}_chart`,
          height: 600,
          width: 900,
        });
      }
    } catch (e) {
      console.error("Failed to download chart image:", e);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header with Title and Mode Toggles */}
      <div className="p-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-muted/20">
        <div>
          <div className="flex items-center space-x-2">
            <BarChart2 className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">{chartSpec.title}</h3>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/20 text-primary uppercase font-mono font-bold">
              {chartSpec.chart_type}
            </span>
          </div>
          {chartSpec.subtitle && (
            <p className="text-xs text-muted-foreground mt-0.5">{chartSpec.subtitle}</p>
          )}
        </div>

        {/* View Mode & Download Controls */}
        <div className="flex items-center space-x-1 self-end sm:self-auto">
          {!chartSpec.fallback_to_table && (
            <div className="flex items-center bg-background rounded-lg border border-border p-0.5 text-xs">
              <button
                onClick={() => setViewMode("chart")}
                className={`px-2.5 py-1 rounded flex items-center space-x-1 transition-colors ${
                  viewMode === "chart"
                    ? "bg-primary text-white font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Chart</span>
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`px-2.5 py-1 rounded flex items-center space-x-1 transition-colors ${
                  viewMode === "table"
                    ? "bg-primary text-white font-medium"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <TableIcon className="w-3.5 h-3.5" />
                <span>Table</span>
              </button>
            </div>
          )}

          {viewMode === "chart" && !chartSpec.fallback_to_table && (
            <button
              onClick={handleDownload}
              title="Download PNG chart image"
              className="p-1.5 rounded-lg border border-border bg-background hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Render Error Alert if fallback occurred */}
      {renderError && (
        <div className="p-3 bg-warning/10 border-b border-warning/20 text-warning text-xs">
          Notice: Chart rendering was substituted with tabular presentation ({renderError}).
        </div>
      )}

      {/* Main View Area */}
      {viewMode === "chart" && !chartSpec.fallback_to_table ? (
        <div className="relative min-h-[360px] p-2 bg-background/20">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10 text-xs text-muted-foreground font-mono">
              Rendering interactive Plotly visualization...
            </div>
          )}
          <div ref={containerRef} className="w-full h-[360px]" />
          {chartSpec.alt_text && (
            <div className="p-2 text-[11px] text-muted-foreground text-center italic border-t border-border/40">
              {chartSpec.alt_text}
            </div>
          )}
        </div>
      ) : (
        /* Data Table Fallback View */
        <div className="p-4 space-y-2">
          {queryResult && queryResult.rows.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted text-muted-foreground font-semibold">
                  <tr>
                    {queryResult.columns.map((col) => (
                      <th key={col} className="p-2.5">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {queryResult.rows.slice(0, 20).map((row, idx) => (
                    <tr key={idx} className="hover:bg-muted/20">
                      {queryResult.columns.map((col) => (
                        <td key={col} className="p-2.5 font-mono text-foreground">
                          {row[col] !== null ? String(row[col]) : <span className="text-muted-foreground">NULL</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {queryResult.rows.length > 20 && (
                <div className="p-2 text-center text-xs text-muted-foreground bg-muted/10">
                  Showing first 20 of {queryResult.row_count} rows.
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-muted-foreground">
              No tabular records to display.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

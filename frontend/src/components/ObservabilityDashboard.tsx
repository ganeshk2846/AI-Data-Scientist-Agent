"use client";

import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchObservabilityMetrics, fetchRecentTraces } from "@/lib/api";
import { RunTraceRecord } from "@/types/api";
import {
  Activity,
  CheckCircle2,
  Clock,
  Code2,
  Copy,
  Check,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Zap,
  Search,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Filter,
} from "lucide-react";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { useClipboard } from "@/lib/useClipboard";

export function ObservabilityDashboard() {
  const { copy, isCopied } = useClipboard(2000);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null);

  const {
    data: metrics,
    isLoading: loadingMetrics,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ["observabilityMetrics"],
    queryFn: fetchObservabilityMetrics,
    refetchInterval: 10000,
  });

  const {
    data: traces,
    isLoading: loadingTraces,
    refetch: refetchTraces,
  } = useQuery({
    queryKey: ["recentTraces"],
    queryFn: () => fetchRecentTraces(50),
    refetchInterval: 10000,
  });

  const handleRefresh = () => {
    refetchMetrics();
    refetchTraces();
  };

  const isLoading = loadingMetrics || loadingTraces;

  // Filtered traces based on search and status
  const filteredTraces = useMemo(() => {
    return (traces || []).filter((trace) => {
      const matchesSearch =
        trace.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
        trace.intent.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (trace.sql_executed && trace.sql_executed.toLowerCase().includes(searchTerm.toLowerCase()));

      if (!matchesSearch) return false;

      if (statusFilter === "all") return true;
      return trace.verification_status.toLowerCase() === statusFilter.toLowerCase();
    });
  }, [traces, searchTerm, statusFilter]);

  return (
    <section className="space-y-6">
      {/* 1. Header & Metric Controls */}
      <div className="p-6 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-primary/15 text-primary">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-foreground">
                    Telemetry & Observability Cockpit
                  </h2>
                  <Badge variant="primary" size="xs">
                    Non-Parametric Percentiles (p50 / p95 / p99)
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  High-resolution execution metrics and safety audits persisted in <code className="font-mono text-foreground">agent_app.sqlite</code>
                </p>
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            isLoading={isLoading}
            icon={!isLoading ? <RefreshCw className="w-3.5 h-3.5" /> : undefined}
          >
            Refresh Telemetry
          </Button>
        </div>

        {/* 2. Key Operational Metrics Grid (7 Columns) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 pt-2">
          {/* Total Runs */}
          <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <Zap className="w-3.5 h-3.5 text-primary" />
              <span>Total Runs</span>
            </span>
            <p className="text-xl font-bold text-foreground font-mono">
              {metrics?.total_runs ?? 0}
            </p>
          </div>

          {/* Success Rate */}
          <div className="p-3.5 rounded-xl border border-success/30 bg-success/10 space-y-1">
            <span className="text-[11px] text-success font-medium flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-success" />
              <span>Success Rate</span>
            </span>
            <p className="text-xl font-bold text-success font-mono">
              {metrics?.success_rate_pct ?? 100}%
            </p>
          </div>

          {/* Latency p50 */}
          <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-primary" />
              <span>Latency p50</span>
            </span>
            <p className="text-xl font-bold text-foreground font-mono">
              {metrics?.latency_p50_ms ? `${metrics.latency_p50_ms.toFixed(1)}ms` : "0.0ms"}
            </p>
          </div>

          {/* Latency p95 */}
          <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-warning" />
              <span>Latency p95</span>
            </span>
            <p className="text-xl font-bold text-warning font-mono">
              {metrics?.latency_p95_ms ? `${metrics.latency_p95_ms.toFixed(1)}ms` : "0.0ms"}
            </p>
          </div>

          {/* Latency p99 */}
          <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-destructive" />
              <span>Latency p99</span>
            </span>
            <p className="text-xl font-bold text-destructive font-mono">
              {metrics?.latency_p99_ms ? `${metrics.latency_p99_ms.toFixed(1)}ms` : "0.0ms"}
            </p>
          </div>

          {/* Average Latency */}
          <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
            <span className="text-[11px] text-muted-foreground">Avg Latency</span>
            <p className="text-xl font-bold text-foreground font-mono">
              {metrics?.avg_latency_ms ? `${metrics.avg_latency_ms.toFixed(1)}ms` : "0.0ms"}
            </p>
          </div>

          {/* Safety Blocks */}
          <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5 text-warning" />
              <span>Security Blocks</span>
            </span>
            <p className="text-xl font-bold text-warning font-mono">
              {metrics?.safety_block_count ?? 0}
            </p>
          </div>
        </div>

        {/* 3. Recorded Error Class Breakdown Strip */}
        {metrics?.error_classes_breakdown &&
          Object.keys(metrics.error_classes_breakdown).length > 0 && (
            <div className="pt-3 border-t border-border/60 flex items-center gap-2 text-xs flex-wrap">
              <span className="text-muted-foreground font-medium flex items-center gap-1">
                <Filter className="w-3 h-3 text-warning" />
                <span>Recorded Safety Anomalies & Refusals:</span>
              </span>
              {Object.entries(metrics.error_classes_breakdown).map(([errClass, count]) => (
                <Badge key={errClass} variant="warning" size="xs">
                  {errClass}: {count}
                </Badge>
              ))}
            </div>
          )}
      </div>

      {/* 4. Execution Traces Table & Inspector */}
      <div className="p-6 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">
              Recent Execution Traces ({filteredTraces.length})
            </h3>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end flex-wrap">
            {/* Status Filter Buttons */}
            <div className="flex items-center gap-1 bg-background/80 p-0.5 rounded-lg border border-border text-xs">
              {["all", "verified", "blocked", "refused"].map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setStatusFilter(status)}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium capitalize transition-colors cursor-pointer ${
                    statusFilter === status
                      ? "bg-primary text-white"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {status}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-muted-foreground pointer-events-none" />
              <input
                type="text"
                placeholder="Search traces..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-2.5 py-1 text-xs bg-background/60 border border-border rounded-lg text-foreground focus:outline-none focus:border-primary placeholder:text-muted-foreground/70 w-36 sm:w-44"
              />
            </div>
          </div>
        </div>

        {/* Traces Table */}
        {filteredTraces.length === 0 ? (
          <div className="p-10 text-center text-xs text-muted-foreground border border-border/60 rounded-xl bg-background/40">
            No execution traces match your search criteria.
          </div>
        ) : (
          <div className="overflow-x-auto border border-border/70 rounded-xl bg-background/40">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-muted/70 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="p-3 font-mono">Timestamp</th>
                  <th className="p-3">Query</th>
                  <th className="p-3">Intent</th>
                  <th className="p-3 font-mono">Latency</th>
                  <th className="p-3 font-mono">Rows</th>
                  <th className="p-3">Verification</th>
                  <th className="p-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {filteredTraces.map((trace: RunTraceRecord) => {
                  const isSuccess = trace.verification_status === "verified";
                  const isBlocked = trace.verification_status === "blocked";
                  const isRefused = trace.verification_status === "refused";
                  const isExpanded = expandedTraceId === trace.run_id;

                  let latencyColor = "text-success font-semibold";
                  if (trace.latency_ms > 1000) latencyColor = "text-warning font-semibold";
                  if (trace.latency_ms > 3000) latencyColor = "text-destructive font-semibold";

                  return (
                    <React.Fragment key={trace.run_id}>
                      <tr className="hover:bg-muted/30 transition-colors">
                        <td className="p-3 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                          {new Date(trace.created_at).toLocaleTimeString()}
                        </td>
                        <td
                          className="p-3 font-medium text-foreground max-w-[280px] truncate"
                          title={trace.query}
                        >
                          {trace.query}
                        </td>
                        <td className="p-3">
                          <Badge variant="primary" size="xs" className="capitalize">
                            {trace.intent}
                          </Badge>
                        </td>
                        <td className={`p-3 font-mono ${latencyColor}`}>
                          {trace.latency_ms.toFixed(1)}ms
                        </td>
                        <td className="p-3 font-mono text-muted-foreground">
                          {trace.row_count}
                        </td>
                        <td className="p-3">
                          <Badge
                            variant={isSuccess ? "success" : isBlocked ? "destructive" : isRefused ? "warning" : "default"}
                            size="xs"
                            className="capitalize"
                          >
                            {isSuccess && <CheckCircle2 className="w-3 h-3" />}
                            {isBlocked && <ShieldAlert className="w-3 h-3" />}
                            {isRefused && <ShieldCheck className="w-3 h-3" />}
                            <span>{trace.verification_status}</span>
                          </Badge>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-1.5">
                            {trace.sql_executed && (
                              <Button
                                variant="outline"
                                size="xs"
                                onClick={() => copy(trace.sql_executed!, trace.run_id)}
                                icon={
                                  isCopied(trace.run_id) ? (
                                    <Check className="w-3 h-3 text-success" />
                                  ) : (
                                    <Copy className="w-3 h-3" />
                                  )
                                }
                                title="Copy SQL statement"
                              >
                                {isCopied(trace.run_id) ? "Copied" : "SQL"}
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                setExpandedTraceId(isExpanded ? null : trace.run_id)
                              }
                              title="Toggle trace details"
                            >
                              {isExpanded ? (
                                <ChevronUp className="w-3.5 h-3.5" />
                              ) : (
                                <ChevronDown className="w-3.5 h-3.5" />
                              )}
                            </Button>
                          </div>
                        </td>
                      </tr>

                      {/* Expanded Row Detail */}
                      {isExpanded && (
                        <tr className="bg-muted/20">
                          <td colSpan={7} className="p-4 space-y-2.5">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                              <div className="p-2 rounded-lg bg-background/80 border border-border/60">
                                <span className="text-[10px] text-muted-foreground block">RUN ID</span>
                                <span className="text-foreground truncate block">{trace.run_id}</span>
                              </div>
                              <div className="p-2 rounded-lg bg-background/80 border border-border/60">
                                <span className="text-[10px] text-muted-foreground block">SESSION ID</span>
                                <span className="text-foreground truncate block">{trace.session_id}</span>
                              </div>
                              <div className="p-2 rounded-lg bg-background/80 border border-border/60">
                                <span className="text-[10px] text-muted-foreground block">ESTIMATED COST</span>
                                <span className="text-foreground block">${trace.cost_estimate_usd.toFixed(6)}</span>
                              </div>
                              <div className="p-2 rounded-lg bg-background/80 border border-border/60">
                                <span className="text-[10px] text-muted-foreground block">ERROR CLASS</span>
                                <span className="text-warning block">{trace.error_class || "None"}</span>
                              </div>
                            </div>

                            {trace.sql_executed ? (
                              <div className="space-y-1">
                                <span className="text-[10px] font-mono font-bold text-muted-foreground uppercase">
                                  Executed SQL Statement:
                                </span>
                                <pre className="p-3 rounded-lg bg-background text-primary font-mono text-xs overflow-x-auto border border-border/80">
                                  <code>{trace.sql_executed}</code>
                                </pre>
                              </div>
                            ) : (
                              <p className="text-xs text-muted-foreground italic">
                                No database SQL was executed for this query (e.g. refused by Answerability Gate or clarification requested).
                              </p>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

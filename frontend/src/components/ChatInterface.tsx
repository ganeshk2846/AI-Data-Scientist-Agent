"use client";

import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { executeChatQuery } from "@/lib/api";
import { MultiAgentWorkflowResult } from "@/types/api";
import { PlotlyChartRenderer } from "./PlotlyChartRenderer";
import {
  AlertCircle,
  ArrowRight,
  BarChart2,
  Check,
  CheckCircle2,
  Clock,
  Code2,
  Copy,
  Database,
  FileText,
  GitBranch,
  HelpCircle,
  Layers,
  Lightbulb,
  MessageSquare,
  Play,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Table,
  Wrench,
} from "lucide-react";

const SUGGESTED_QUERIES = [
  "Show orders by status and their total amount",
  "What are our total sales and order counts by year?",
  "What are the top 5 product categories by revenue?",
  "How many customers belong to each customer segment?",
  "What is the churn risk and revenue at risk across customer segments?",
  "compare revenue", // Triggers clarification
  "What is the current bitcoin price?", // Triggers answerability refusal
];

const WORKFLOW_STEPS = [
  { key: "understanding_question", label: "Router & Gate" },
  { key: "retrieving_schema", label: "Schema Grounder" },
  { key: "generating_query", label: "SQL Generator" },
  { key: "validating_query", label: "AST Guardrail & Repair" },
  { key: "running_query", label: "Read-Only Runner" },
  { key: "verifying_results", label: "Verifier & Chart Spec" },
  { key: "composing_answer", label: "Executive Composer" },
];

export function ChatInterface() {
  const [sessionId, setSessionId] = useState<string>("sess-default");

  useEffect(() => {
    setSessionId("sess-" + Math.random().toString(36).substring(2, 9));
  }, []);
  const [queryInput, setQueryInput] = useState("");
  const [activeTab, setActiveTab] = useState<"narrative" | "chart" | "analysis" | "sql" | "data" | "plan" | "trace">("narrative");
  const [copiedSql, setCopiedSql] = useState(false);

  const queryMutation = useMutation({
    mutationFn: (text: string) => executeChatQuery(text, sessionId),
  });

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!queryInput.trim() || queryMutation.isPending) return;
    queryMutation.mutate(queryInput.trim());
  };

  const handleSelectSuggested = (text: string) => {
    setQueryInput(text);
    queryMutation.mutate(text);
  };

  const handleClarificationOption = (inferredQuery: string) => {
    setQueryInput(inferredQuery);
    queryMutation.mutate(inferredQuery);
  };

  const handleNewSession = () => {
    setSessionId("sess-" + Math.random().toString(36).substring(2, 9));
    setQueryInput("");
    queryMutation.reset();
  };

  const handleCopySql = (sql: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const result: MultiAgentWorkflowResult | undefined = queryMutation.data;

  return (
    <section className="space-y-6">
      {/* Question Input Card */}
      <div className="p-6 rounded-xl border border-border bg-card space-y-4">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-5 h-5 text-primary" />
          <h2 className="text-base font-semibold text-foreground">
            Multi-Agent Conversational BI Interface
          </h2>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/20 text-primary font-mono">
            Phase 8 Shared Memory Active
          </span>
          <div className="ml-auto flex items-center space-x-2">
            <span suppressHydrationWarning className="text-[11px] font-mono text-muted-foreground px-2 py-0.5 rounded bg-muted/60">
              {sessionId}
            </span>
            <button
              onClick={handleNewSession}
              type="button"
              className="text-xs px-2.5 py-1 rounded-md border border-border bg-background hover:bg-muted text-foreground transition-colors"
            >
              + New Session
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            placeholder="Ask any business question (e.g. 'Show orders by status and total revenue')..."
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            disabled={queryMutation.isPending}
            className="w-full pl-4 pr-32 py-3 text-sm bg-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!queryInput.trim() || queryMutation.isPending}
            className="absolute right-2 top-2 px-4 py-1.5 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 disabled:opacity-40 flex items-center space-x-1.5 transition-colors"
          >
            {queryMutation.isPending ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            <span>{queryMutation.isPending ? "Executing..." : "Ask Agent"}</span>
          </button>
        </form>

        {/* Suggested Queries */}
        <div className="flex items-center space-x-2 text-xs flex-wrap gap-y-2">
          <span className="text-muted-foreground flex items-center space-x-1">
            <Lightbulb className="w-3.5 h-3.5 text-warning" />
            <span>Try:</span>
          </span>
          {SUGGESTED_QUERIES.map((sq, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSelectSuggested(sq)}
              disabled={queryMutation.isPending}
              className="px-2.5 py-1 rounded-lg bg-background/60 border border-border hover:border-primary/50 text-foreground/80 hover:text-foreground text-[11px] transition-colors"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Loading & Progress Stepper */}
      {queryMutation.isPending && (
        <div className="p-6 rounded-xl border border-primary/30 bg-card space-y-4">
          <div className="flex items-center space-x-2 text-sm text-primary font-medium">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Executing Multi-Agent DAG Orchestration...</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 text-xs">
            {WORKFLOW_STEPS.map((s, idx) => (
              <div
                key={s.key}
                className="p-2.5 rounded-lg border border-border bg-background/40 flex flex-col justify-between"
              >
                <span className="text-[10px] text-muted-foreground font-mono">0{idx + 1}</span>
                <span className="text-[11px] font-medium text-foreground truncate mt-1">
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Card */}
      {queryMutation.isError && (
        <div className="p-6 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-sm">Query Execution Failed</h3>
            <p className="text-xs text-foreground/80 mt-1">
              {queryMutation.error?.message || "An unexpected error occurred during execution."}
            </p>
          </div>
        </div>
      )}

      {/* Results View */}
      {result && !queryMutation.isPending && (
        <div className="p-6 rounded-xl border border-border bg-card space-y-6">
          {/* Header & Meta */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-border gap-2">
            <div>
              <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/20 text-primary font-medium capitalize">
                  {result.route.intent} Plan
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  Confidence: {(result.route.confidence * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  Execution: {result.total_duration_ms.toFixed(0)}ms
                </span>

                {/* Repair Badge if repair attempts happened */}
                {result.repair_attempts.length > 0 && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-warning/20 text-warning border border-warning/30 flex items-center space-x-1 font-mono">
                    <Wrench className="w-3 h-3" />
                    <span>Repaired ({result.repair_attempts.length}/2)</span>
                  </span>
                )}

                {/* Chart Spec Badge */}
                {result.chart_spec && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-foreground/90 font-mono flex items-center space-x-1">
                    <BarChart2 className="w-3 h-3 text-primary" />
                    <span className="capitalize">{result.chart_spec.chart_type} Chart</span>
                  </span>
                )}
              </div>
              <p className="text-sm font-medium text-foreground mt-1.5 italic">
                "{result.query}"
              </p>
              {result.selected_tables.length > 0 && (
                <div className="flex items-center space-x-1.5 mt-2 flex-wrap gap-1">
                  <span className="text-[11px] text-muted-foreground font-mono">Grounded Tables (RRF):</span>
                  {result.selected_tables.map((tbl) => (
                    <span
                      key={tbl}
                      className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-mono"
                    >
                      {tbl}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* View Tabs */}
            <div className="flex items-center space-x-1 p-1 bg-background rounded-lg border border-border text-xs flex-wrap">
              {[
                { key: "narrative", label: "Executive Answer", icon: FileText },
                ...(result.chart_spec && !result.chart_spec.fallback_to_table
                  ? [{ key: "chart", label: `Chart (${result.chart_spec.chart_type})`, icon: BarChart2 }]
                  : []),
                ...(result.analysis_result
                  ? [
                      {
                        key: "analysis",
                        label: `Analysis: ${result.analysis_result.tool_name}`,
                        icon: Sparkles,
  TrendingUp,
                      },
                    ]
                  : []),
                {
                  key: "plan",
                  label: `Execution DAG (${result.plan?.steps.length ?? 0})`,
                  icon: GitBranch,
                },
                { key: "sql", label: "Validated SQL", icon: Code2 },
                {
                  key: "data",
                  label: `Data Table (${result.query_result?.row_count ?? 0})`,
                  icon: Table,
                },
                { key: "trace", label: "Pipeline Trace", icon: Clock },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as any)}
                    className={`px-3 py-1 rounded-md flex items-center space-x-1.5 transition-colors ${
                      isActive
                        ? "bg-primary text-white font-medium"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Clarification Alert if triggered */}
          {result.clarification?.needs_clarification && (
            <div className="p-5 rounded-xl border border-primary/40 bg-primary/10 space-y-4">
              <div className="flex items-start space-x-3">
                <HelpCircle className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <h3 className="font-semibold text-sm text-foreground">
                    Clarification Required: {result.clarification.question}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {result.clarification.ambiguity_reason}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                {result.clarification.options.map((opt) => (
                  <button
                    key={opt.option_id}
                    onClick={() => handleClarificationOption(opt.inferred_query)}
                    className="p-3 rounded-lg border border-border bg-background hover:border-primary text-left text-xs space-y-1 transition-all group"
                  >
                    <div className="flex items-center justify-between font-medium text-foreground group-hover:text-primary">
                      <span>{opt.label}</span>
                      <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-[11px] text-muted-foreground">{opt.description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Answerability Refusal Alert if triggered */}
          {!result.answerability.is_answerable && (
            <div className="p-5 rounded-xl border border-warning/40 bg-warning/10 space-y-3">
              <div className="flex items-start space-x-3">
                <ShieldAlert className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <h3 className="font-semibold text-sm text-warning">
                    Honest Refusal: Question Outside Warehouse Scope
                  </h3>
                  <p className="text-xs text-foreground/80">
                    {result.answerability.refusal_reason}
                  </p>
                </div>
              </div>

              {result.answerability.available_alternatives.length > 0 && (
                <div className="pt-2 border-t border-warning/20">
                  <span className="text-xs font-semibold text-foreground">
                    Supported warehouse domains you can query:
                  </span>
                  <ul className="mt-1 list-disc list-inside text-xs text-muted-foreground space-y-0.5">
                    {result.answerability.available_alternatives.map((alt, i) => (
                      <li key={i}>{alt}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Contextual Analytical Follow-up Questions */}
              {result.suggested_followups && result.suggested_followups.length > 0 && (
                <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-semibold text-primary">
                    <TrendingUp className="w-3.5 h-3.5" />
                    <span>Suggested Next Questions (Click to Investigate):</span>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {result.suggested_followups.map((qText, i) => (
                      <button
                        key={i}
                        onClick={() => handleSelectSuggested(qText)}
                        className="px-3 py-1.5 rounded-lg border border-border bg-card hover:border-primary text-left text-xs text-foreground/90 hover:text-primary transition-all flex items-center space-x-1.5 group"
                      >
                        <span>{qText}</span>
                        <ArrowRight className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}

          {/* Tab 1: Executive Answer Narrative */}
          {activeTab === "narrative" && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-background/50 border border-border prose prose-invert prose-sm max-w-none text-foreground text-xs leading-relaxed">
                <div className="whitespace-pre-wrap">{result.composed_answer}</div>
              </div>

              {/* Key Findings */}
              {result.key_findings.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-foreground flex items-center space-x-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                    <span>Verified Factual Findings</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {result.key_findings.map((f, i) => (
                      <div
                        key={i}
                        className="p-2.5 rounded-lg border border-border bg-background/30 text-muted-foreground"
                      >
                        {f}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Caveats */}
              {result.limitations.length > 0 && (
                <div className="p-3 rounded-lg border border-warning/30 bg-warning/10 text-warning text-xs space-y-1">
                  <span className="font-semibold flex items-center space-x-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Data Coverage & Caveats</span>
                  </span>
                  <ul className="list-disc list-inside space-y-0.5 text-foreground/80 pl-1">
                    {result.limitations.map((lim, i) => (
                      <li key={i}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}


          
          {/* Tab: Interactive Plotly Visual Chart */}
          {activeTab === "chart" && result.chart_spec && (
            <div className="space-y-4">
              <PlotlyChartRenderer chartSpec={result.chart_spec} queryResult={result.query_result} />
            </div>
          )}

          {/* Tab: Deterministic Analysis Tool Artefact */}
          {activeTab === "analysis" && result.analysis_result && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs pb-2 border-b border-border">
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <span className="font-semibold text-foreground capitalize">
                    {result.analysis_result.tool_name.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-primary/20 text-primary font-mono">
                    Method: {result.analysis_result.provenance.method_name}
                  </span>
                </div>
                <span className="text-[11px] text-muted-foreground font-mono">
                  Window: {result.analysis_result.provenance.time_window}
                </span>
              </div>

              {/* Churn Risk Artefact */}
              {result.analysis_result.churn_risk && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg border border-border bg-background/50">
                      <span className="text-[11px] text-muted-foreground">Total Customers</span>
                      <p className="text-lg font-bold text-foreground">
                        {result.analysis_result.churn_risk.total_customers_analyzed.toLocaleString()}
                      </p>
                    </div>
                    <div className="p-3 rounded-lg border border-destructive/30 bg-destructive/10">
                      <span className="text-[11px] text-destructive font-medium">Revenue at Risk</span>
                      <p className="text-lg font-bold text-destructive">
                        ${result.analysis_result.churn_risk.total_revenue_at_risk.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </p>
                    </div>
                    <div className="p-3 rounded-lg border border-border bg-background/50">
                      <span className="text-[11px] text-muted-foreground">Threshold</span>
                      <p className="text-lg font-bold text-foreground">
                        {result.analysis_result.churn_risk.inactivity_threshold_days} Days Inactivity
                      </p>
                    </div>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-border bg-background/30">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-muted text-muted-foreground font-semibold">
                        <tr>
                          <th className="p-2.5">Rank</th>
                          <th className="p-2.5">Segment</th>
                          <th className="p-2.5">Customers</th>
                          <th className="p-2.5">Churn Rate (95% CI)</th>
                          <th className="p-2.5">Historical Spend</th>
                          <th className="p-2.5">Revenue at Risk</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {result.analysis_result.churn_risk.segments.map((seg) => (
                          <tr key={seg.segment_name} className="hover:bg-muted/20">
                            <td className="p-2.5 font-bold font-mono">#{seg.actionability_rank}</td>
                            <td className="p-2.5 font-semibold text-foreground">{seg.segment_name}</td>
                            <td className="p-2.5 font-mono">{seg.customer_count.toLocaleString()}</td>
                            <td className="p-2.5 font-mono">
                              <span className="font-semibold text-warning">{seg.churn_rate_pct}%</span>
                              <span className="text-[10px] text-muted-foreground ml-1">
                                ({seg.confidence_interval_low}% - {seg.confidence_interval_high}%)
                              </span>
                            </td>
                            <td className="p-2.5 font-mono">${seg.total_historical_spend.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                            <td className="p-2.5 font-mono font-semibold text-destructive">
                              ${seg.revenue_at_risk.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Anomaly Detection Artefact */}
              {result.analysis_result.anomaly_detection && (
                <div className="space-y-3">
                  <div className="flex items-center space-x-3 text-xs">
                    <span className="text-muted-foreground">
                      Anomalies detected: <strong className="text-foreground">{result.analysis_result.anomaly_detection.anomaly_count}</strong> of {result.analysis_result.anomaly_detection.total_data_points} points
                    </span>
                    <span className="text-muted-foreground">
                      Threshold: |z| &ge; {result.analysis_result.anomaly_detection.threshold}
                    </span>
                  </div>

                  {result.analysis_result.anomaly_detection.anomalies.filter(a => a.is_anomaly).length > 0 && (
                    <div className="overflow-x-auto rounded-lg border border-border bg-background/30">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-muted text-muted-foreground font-semibold">
                          <tr>
                            <th className="p-2.5">Date</th>
                            <th className="p-2.5">Actual Value</th>
                            <th className="p-2.5">Expected Baseline</th>
                            <th className="p-2.5">Z-Score</th>
                            <th className="p-2.5">Severity</th>
                            <th className="p-2.5">Data Quality Screen</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {result.analysis_result.anomaly_detection.anomalies.filter(a => a.is_anomaly).map((anom, idx) => (
                            <tr key={idx} className="hover:bg-muted/20">
                              <td className="p-2.5 font-mono">{anom.date}</td>
                              <td className="p-2.5 font-mono font-bold text-foreground">{anom.actual_value}</td>
                              <td className="p-2.5 font-mono text-muted-foreground">{anom.expected_value}</td>
                              <td className="p-2.5 font-mono text-warning">{anom.z_score}</td>
                              <td className="p-2.5">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                  anom.severity === "severe" ? "bg-destructive/20 text-destructive" : "bg-warning/20 text-warning"
                                }`}>
                                  {anom.severity.toUpperCase()}
                                </span>
                              </td>
                              <td className="p-2.5 text-[11px] text-muted-foreground">
                                {anom.quality_flag ? (
                                  <span className="text-destructive font-mono">{anom.quality_flag}</span>
                                ) : (
                                  "Pass"
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Forecast Artefact */}
              {result.analysis_result.forecast && (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="p-2.5 rounded border border-border bg-background/40">
                      <span className="text-muted-foreground">Model</span>
                      <p className="font-semibold text-foreground">{result.analysis_result.forecast.model_used}</p>
                    </div>
                    <div className="p-2.5 rounded border border-border bg-background/40">
                      <span className="text-muted-foreground">Backtest MAE</span>
                      <p className="font-semibold text-foreground">{result.analysis_result.forecast.backtest_mae}</p>
                    </div>
                    <div className="p-2.5 rounded border border-border bg-background/40">
                      <span className="text-muted-foreground">Backtest MAPE</span>
                      <p className="font-semibold text-foreground">{result.analysis_result.forecast.backtest_mape_pct}%</p>
                    </div>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-border bg-background/30">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-muted text-muted-foreground font-semibold">
                        <tr>
                          <th className="p-2.5">Forecast Date</th>
                          <th className="p-2.5">Point Forecast</th>
                          <th className="p-2.5">80% Interval</th>
                          <th className="p-2.5">95% Interval</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {result.analysis_result.forecast.points.map((pt) => (
                          <tr key={pt.date} className="hover:bg-muted/20">
                            <td className="p-2.5 font-mono">{pt.date}</td>
                            <td className="p-2.5 font-mono font-bold text-primary">{pt.point_forecast}</td>
                            <td className="p-2.5 font-mono text-muted-foreground">
                              [{pt.lower_bound_80} - {pt.upper_bound_80}]
                            </td>
                            <td className="p-2.5 font-mono text-muted-foreground">
                              [{pt.lower_bound_95} - {pt.upper_bound_95}]
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Optimization Artefact */}
              {result.analysis_result.optimization && (
                <div className="space-y-3">
                  <div className="p-3 rounded-lg border border-border bg-background/40 flex items-center justify-between text-xs">
                    <div>
                      <span className="text-muted-foreground">Total Budget Allocated</span>
                      <p className="text-base font-bold text-foreground">
                        ${result.analysis_result.optimization.total_budget.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Expected Return</span>
                      <p className="text-base font-bold text-success">
                        ${result.analysis_result.optimization.expected_total_revenue.toLocaleString()}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1.5 font-mono text-xs">
                    {Object.entries(result.analysis_result.optimization.allocations).map(([ch, alloc]) => (
                      <div key={ch} className="p-2 rounded border border-border bg-background/30 flex items-center justify-between">
                        <span className="font-semibold text-foreground">{ch}</span>
                        <span className="text-primary font-bold">${alloc.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Provenance Assumptions */}
              {result.analysis_result.provenance.assumptions.length > 0 && (
                <div className="p-3 rounded-lg bg-background/40 border border-border text-xs space-y-1">
                  <span className="font-semibold text-muted-foreground">Method Assumptions & Provenance:</span>
                  <ul className="list-disc list-inside space-y-0.5 text-muted-foreground/80 pl-1">
                    {result.analysis_result.provenance.assumptions.map((assump, i) => (
                      <li key={i}>{assump}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Execution DAG Plan */}
          {activeTab === "plan" && result.plan && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-mono">
                  Planner DAG Goal: {result.plan.goal}
                </span>
                <span className="text-xs text-primary font-mono font-medium">
                  {result.plan.steps.length} Steps
                </span>
              </div>

              <div className="space-y-2 font-mono text-xs">
                {result.plan.steps.map((step, idx) => (
                  <div
                    key={step.step_id}
                    className="p-3 rounded-lg border border-border bg-background/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">
                        {idx + 1}
                      </span>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-foreground">{step.step_id}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            {step.tool_name}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted-foreground font-sans mt-0.5">
                          {step.description}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 text-[11px]">
                      {step.dependencies.length > 0 && (
                        <span className="text-muted-foreground">
                          Depends on: {step.dependencies.join(", ")}
                        </span>
                      )}
                      <span className="px-2 py-0.5 rounded bg-success/20 text-success font-medium">
                        Completed
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab 3: Validated SQL & Repair Info */}
          {activeTab === "sql" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-mono">
                  AST Validated SQLite Statement (sqlglot)
                </span>
                {result.sanitized_sql && (
                  <button
                    onClick={() => handleCopySql(result.sanitized_sql!)}
                    className="px-2.5 py-1 rounded bg-background border border-border hover:bg-muted text-foreground text-xs flex items-center space-x-1"
                  >
                    {copiedSql ? (
                      <Check className="w-3 h-3 text-success" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                    <span>{copiedSql ? "Copied" : "Copy SQL"}</span>
                  </button>
                )}
              </div>

              <pre className="p-4 rounded-lg bg-background font-mono text-xs text-primary overflow-x-auto border border-border">
                <code>{result.sanitized_sql || "-- No executable SQL produced (Refused/Ambiguous)"}</code>
              </pre>

              {/* Repair details if repair occurred */}
              {result.repair_attempts.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-border">
                  <h4 className="text-xs font-semibold text-foreground flex items-center space-x-1.5">
                    <Wrench className="w-3.5 h-3.5 text-warning" />
                    <span>Automatic SQL Repair Trail ({result.repair_attempts.length} attempts)</span>
                  </h4>
                  {result.repair_attempts.map((att) => (
                    <div
                      key={att.attempt_number}
                      className="p-3 rounded-lg border border-warning/30 bg-warning/5 text-xs font-mono space-y-1.5"
                    >
                      <div className="flex justify-between font-semibold text-warning">
                        <span>Attempt {att.attempt_number} of 2</span>
                        <span>{att.validation_passed ? "Validation Succeeded" : "Validation Failed"}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground font-sans">
                        Error addressed: {att.error_message}
                      </p>
                      <pre className="p-2 rounded bg-background text-[11px] text-foreground/80 overflow-x-auto">
                        <code>{att.repaired_sql}</code>
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Data Table */}
          {activeTab === "data" && (
            <div className="space-y-3">
              {!result.query_result || result.query_result.rows.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No records returned for this query.
                </div>
              ) : (
                <div className="overflow-x-auto border border-border rounded-lg">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-background/80 border-b border-border text-muted-foreground font-medium">
                      <tr>
                        {result.query_result.columns.map((col) => (
                          <th key={col} className="p-2.5 font-mono">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {result.query_result.rows.slice(0, 50).map((row, idx) => (
                        <tr key={idx} className="hover:bg-muted/30">
                          {result.query_result!.columns.map((col) => (
                            <td key={col} className="p-2.5 font-mono text-foreground/90">
                              {row[col] !== null ? String(row[col]) : <span className="text-muted-foreground">NULL</span>}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {result.query_result.rows.length > 50 && (
                    <div className="p-2 text-center text-xs text-muted-foreground bg-background/50 border-t border-border">
                      Showing first 50 of {result.query_result.row_count} rows.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tab 5: Pipeline Trace */}
          {activeTab === "trace" && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-foreground">
                Multi-Agent Execution Trace
              </h4>
              <div className="space-y-1.5 font-mono text-xs">
                {result.trace_steps.map((step, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-background/40 border border-border flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          step.status === "succeeded" ? "bg-success" : "bg-destructive"
                        }`}
                      />
                      <span className="font-semibold text-foreground">{step.step}</span>
                      <span className="text-muted-foreground truncate max-w-[400px]">
                        — {step.message}
                      </span>
                    </div>
                    <span className="text-muted-foreground text-[11px]">
                      {step.duration_ms.toFixed(1)}ms
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

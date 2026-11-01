"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { executeChatQuery } from "@/lib/api";
import { QueryWorkflowResult, StepTrace } from "@/types/api";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Code2,
  Copy,
  Database,
  FileText,
  Lightbulb,
  MessageSquare,
  Play,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Table,
} from "lucide-react";

const SUGGESTED_QUERIES = [
  "Show orders by status and their total amount",
  "What are our total sales and order counts by year?",
  "What are the top 5 product categories by revenue?",
  "How many customers belong to each customer segment?",
];

const WORKFLOW_STEPS = [
  { key: "understanding_question", label: "Router (Intent & Entities)" },
  { key: "retrieving_schema", label: "Schema Grounder" },
  { key: "generating_query", label: "SQL Generator" },
  { key: "validating_query", label: "AST Guardrail (sqlglot)" },
  { key: "running_query", label: "Read-Only SQLite Runner" },
  { key: "verifying_results", label: "Verifier & Sanity Check" },
  { key: "composing_answer", label: "Composer Narrative" },
];

export function ChatInterface() {
  const [queryInput, setQueryInput] = useState("");
  const [activeTab, setActiveTab] = useState<"narrative" | "sql" | "data" | "trace">("narrative");
  const [copiedSql, setCopiedSql] = useState(false);

  const queryMutation = useMutation({
    mutationFn: (text: string) => executeChatQuery(text),
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

  const handleCopySql = (sql: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const result: QueryWorkflowResult | undefined = queryMutation.data;

  return (
    <section className="space-y-6">
      {/* Question Input Card */}
      <div className="p-6 rounded-xl border border-border bg-card space-y-4">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-5 h-5 text-primary" />
          <h2 className="text-base font-semibold text-foreground">
            Natural-Language BI Question Interface
          </h2>
          <span className="text-xs px-2 py-0.5 rounded-full bg-primary/20 text-primary font-mono">
            Vertical Slice Active
          </span>
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
            <span>{queryMutation.isPending ? "Analyzing..." : "Ask Agent"}</span>
          </button>
        </form>

        {/* Suggested Queries */}
        <div className="flex items-center space-x-2 text-xs flex-wrap gap-y-2">
          <span className="text-muted-foreground flex items-center space-x-1">
            <Lightbulb className="w-3.5 h-3.5 text-warning" />
            <span>Suggested:</span>
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
            <span>Executing Grounded Business Intelligence Pipeline...</span>
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
              <div className="flex items-center space-x-2">
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/20 text-primary font-medium capitalize">
                  {result.route.intent} Analysis
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  Confidence: {(result.route.confidence * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  Execution: {result.total_duration_ms.toFixed(0)}ms
                </span>
              </div>
              <p className="text-sm font-medium text-foreground mt-1.5 italic">
                "{result.query}"
              </p>
            </div>

            {/* View Tabs */}
            <div className="flex items-center space-x-1 p-1 bg-background rounded-lg border border-border text-xs">
              {[
                { key: "narrative", label: "Executive Answer", icon: FileText },
                { key: "sql", label: "SQL Query", icon: Code2 },
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

          {/* Tab 1: Executive Answer Narrative */}
          {activeTab === "narrative" && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-background/50 border border-border prose prose-invert prose-sm max-w-none text-foreground text-xs leading-relaxed">
                <div className="whitespace-pre-wrap">{result.composed_answer}</div>
              </div>

              {/* Key Findings Pills */}
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

              {/* Caveats / Limitations */}
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

          {/* Tab 2: SQL Inspector */}
          {activeTab === "sql" && (
            <div className="space-y-3">
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
                <code>{result.sanitized_sql || result.generated_sql}</code>
              </pre>
              <div className="flex items-center space-x-4 text-xs text-muted-foreground font-mono">
                <span>Execution Time: {result.query_result?.execution_time_ms}ms</span>
                <span>•</span>
                <span>Rows Returned: {result.query_result?.row_count}</span>
                <span>•</span>
                <span>Targeted Tables: {result.selected_tables.join(", ")}</span>
              </div>
            </div>
          )}

          {/* Tab 3: Data Table */}
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

          {/* Tab 4: Pipeline Trace */}
          {activeTab === "trace" && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-foreground">
                Deterministic Agent Execution Trace
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

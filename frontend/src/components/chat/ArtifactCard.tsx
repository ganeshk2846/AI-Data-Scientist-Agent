import React from "react";
import {
  MultiAgentWorkflowResult,
} from "@/types/api";
import {
  BarChart2,
  Check,
  CheckCircle2,
  Clock,
  Code2,
  Copy,
  FileText,
  GitBranch,
  ShieldCheck,
  Sparkles,
  Table,
  TrendingUp,
  Wrench,
  ArrowRight,
} from "lucide-react";
import { PlotlyChartRenderer } from "../PlotlyChartRenderer";
import { AnalysisArtifacts } from "./AnalysisArtifacts";
import { DataTable } from "../ui/DataTable";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { useClipboard } from "@/lib/useClipboard";

export interface ArtifactCardProps {
  result: MultiAgentWorkflowResult;
  activeTab?: "narrative" | "chart" | "analysis" | "sql" | "data" | "plan" | "trace";
  onTabChange: (tab: "narrative" | "chart" | "analysis" | "sql" | "data" | "plan" | "trace") => void;
  onSelectFollowUp: (qText: string) => void;
  turnId: string;
}

export function ArtifactCard({
  result,
  activeTab = "narrative",
  onTabChange,
  onSelectFollowUp,
  turnId,
}: ArtifactCardProps) {
  const { copy, isCopied } = useClipboard(2000);

  const TABS = [
    { key: "narrative", label: "Executive Answer", icon: FileText },
    ...(result.chart_spec && !result.chart_spec.fallback_to_table
      ? [{ key: "chart", label: `Chart (${result.chart_spec.chart_type})`, icon: BarChart2 }]
      : []),
    ...(result.analysis_result
      ? [{ key: "analysis", label: `Analysis (${(result.analysis_result as any).tool_name || (result.analysis_result as any).analytical_type || "Decision Support"})`, icon: Sparkles }]
      : []),
    { key: "plan", label: `DAG (${result.plan?.steps.length ?? 0})`, icon: GitBranch },
    { key: "sql", label: "SQL", icon: Code2 },
    { key: "data", label: `Data (${result.query_result?.row_count ?? 0})`, icon: Table },
    { key: "trace", label: "Trace", icon: Clock },
  ] as const;

  return (
    <div className="p-6 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-6">
      {/* Header & Meta Badges */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-border/70 gap-3">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="primary" size="sm" className="capitalize font-semibold">
              {result.route.intent} Plan
            </Badge>
            <Badge variant="mono" size="xs">
              Confidence: {(result.route.confidence * 100).toFixed(0)}%
            </Badge>
            <Badge variant="mono" size="xs">
              Execution: {result.total_duration_ms.toFixed(0)}ms
            </Badge>

            {/* Bounded Repair Badge if repair occurred */}
            {result.repair_attempts && result.repair_attempts.length > 0 && (
              <Badge variant="warning" size="xs" className="flex items-center gap-1 font-mono">
                <Wrench className="w-3 h-3" />
                <span>Repaired ({result.repair_attempts.length}/2)</span>
              </Badge>
            )}

            {/* Chart Spec Badge */}
            {result.chart_spec && (
              <Badge variant="default" size="xs" className="flex items-center gap-1 font-mono">
                <BarChart2 className="w-3 h-3 text-primary" />
                <span className="capitalize">{result.chart_spec.chart_type} Chart</span>
              </Badge>
            )}
          </div>

          {/* Grounded Schema Tables */}
          {result.selected_tables && result.selected_tables.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
              <span className="text-[11px] text-muted-foreground font-mono">
                Grounded Tables (RRF):
              </span>
              {result.selected_tables.map((tbl) => (
                <span
                  key={tbl}
                  className="text-[10px] px-2 py-0.5 rounded-md bg-primary/10 text-primary border border-primary/20 font-mono font-medium"
                >
                  {tbl}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* View Tabs Bar */}
        <div className="flex items-center gap-1 p-1 bg-background/80 rounded-xl border border-border text-xs flex-wrap">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => onTabChange(tab.key as any)}
                className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-medium transition-all cursor-pointer ${
                  isActive
                    ? "bg-primary text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
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
          <div className="flex items-center justify-between pb-1 border-b border-border/50 text-xs">
            <span className="text-muted-foreground font-mono text-[11px]">
              Grounded Executive Synthesis
            </span>
            <Button
              variant="outline"
              size="xs"
              onClick={() => copy(result.composed_answer, `narrative-${turnId}`)}
              icon={
                isCopied(`narrative-${turnId}`) ? (
                  <Check className="w-3 h-3 text-success" />
                ) : (
                  <Copy className="w-3 h-3" />
                )
              }
            >
              {isCopied(`narrative-${turnId}`) ? "Copied" : "Copy Narrative"}
            </Button>
          </div>

          <div className="p-4 rounded-xl bg-background/50 border border-border/80 text-foreground text-xs leading-relaxed">
            <div className="whitespace-pre-wrap font-sans">{result.composed_answer}</div>
          </div>

          {/* Inline Visual Evidence Preview if chart available */}
          {result.chart_spec && !result.chart_spec.fallback_to_table && (
            <div className="pt-2 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                <BarChart2 className="w-4 h-4 text-primary" />
                <span>Visual Evidence Representation</span>
              </div>
              <PlotlyChartRenderer
                chartSpec={result.chart_spec}
                queryResult={result.query_result}
              />
            </div>
          )}

          {/* Verified Factual Findings */}
          {result.key_findings && result.key_findings.length > 0 && (
            <div className="space-y-2 pt-2">
              <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                <span>Verified Factual Findings</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {result.key_findings.map((finding, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl border border-border/70 bg-background/40 text-muted-foreground leading-relaxed"
                  >
                    {finding}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Data Coverage & Caveats */}
          {result.limitations && result.limitations.length > 0 && (
            <div className="p-3.5 rounded-xl border border-warning/30 bg-warning/10 text-warning text-xs space-y-1.5">
              <span className="font-semibold flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Data Coverage & Caveats</span>
              </span>
              <ul className="list-disc list-inside space-y-1 text-foreground/80 pl-1 text-[11px] leading-relaxed">
                {result.limitations.map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Standalone Plotly Chart */}
      {activeTab === "chart" && result.chart_spec && (
        <div className="space-y-4">
          <PlotlyChartRenderer
            chartSpec={result.chart_spec}
            queryResult={result.query_result}
          />
        </div>
      )}

      {/* Tab 3: Deterministic Analysis Tool Artifact */}
      {activeTab === "analysis" && result.analysis_result && (
        <div className="space-y-4">
          <AnalysisArtifacts analysis={result.analysis_result} />
        </div>
      )}

      {/* Tab 4: Execution DAG Plan */}
      {activeTab === "plan" && result.plan && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs pb-1 border-b border-border/50">
            <span className="text-muted-foreground font-mono text-[11px]">
              Planner Goal: {result.plan.goal}
            </span>
            <Badge variant="primary" size="xs">
              {result.plan.steps.length} Steps
            </Badge>
          </div>

          <div className="space-y-2 font-mono text-xs">
            {result.plan.steps.map((step, idx) => (
              <div
                key={step.step_id}
                className="p-3.5 rounded-xl border border-border bg-background/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">
                    {idx + 1}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground">{step.step_id}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground">
                        {step.tool_name}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground font-sans mt-0.5">
                      {step.description}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-[11px]">
                  {step.dependencies.length > 0 && (
                    <span className="text-muted-foreground">
                      Depends on: {step.dependencies.join(", ")}
                    </span>
                  )}
                  <Badge variant="success" size="xs">
                    Completed
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 5: Validated SQL & Bounded Repair Trail */}
      {activeTab === "sql" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs pb-1 border-b border-border/50">
            <span className="text-muted-foreground font-mono text-[11px]">
              AST Validated SQLite Statement (sqlglot)
            </span>
            {result.sanitized_sql && (
              <Button
                variant="outline"
                size="xs"
                onClick={() => copy(result.sanitized_sql!, `sql-${turnId}`)}
                icon={
                  isCopied(`sql-${turnId}`) ? (
                    <Check className="w-3 h-3 text-success" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )
                }
              >
                {isCopied(`sql-${turnId}`) ? "Copied" : "Copy SQL"}
              </Button>
            )}
          </div>

          <pre className="p-4 rounded-xl bg-background/80 font-mono text-xs text-primary overflow-x-auto border border-border leading-relaxed">
            <code>{result.sanitized_sql || "-- No executable SQL produced"}</code>
          </pre>

          {/* Automatic SQL Repair Trail */}
          {result.repair_attempts && result.repair_attempts.length > 0 && (
            <div className="space-y-2.5 pt-2 border-t border-border/60">
              <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Wrench className="w-3.5 h-3.5 text-warning" />
                <span>Automatic SQL Repair Trail ({result.repair_attempts.length} attempts)</span>
              </h4>
              {result.repair_attempts.map((att) => (
                <div
                  key={att.attempt_number}
                  className="p-3.5 rounded-xl border border-warning/30 bg-warning/5 text-xs font-mono space-y-2"
                >
                  <div className="flex justify-between font-semibold text-warning">
                    <span>Attempt {att.attempt_number} of 2</span>
                    <Badge variant={att.validation_passed ? "success" : "warning"} size="xs">
                      {att.validation_passed ? "Validation Succeeded" : "Validation Failed"}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground font-sans">
                    Error addressed: {att.error_message}
                  </p>
                  <pre className="p-2.5 rounded-lg bg-background text-[11px] text-foreground/80 overflow-x-auto border border-border/50">
                    <code>{att.repaired_sql}</code>
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Interactive Data Table */}
      {activeTab === "data" && (
        <div className="space-y-3">
          {!result.query_result || result.query_result.rows.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground border border-border rounded-xl bg-background/40">
              No tabular records returned for this query.
            </div>
          ) : (
            <DataTable
              columns={result.query_result.columns}
              rows={result.query_result.rows}
              totalRowCount={result.query_result.row_count}
              executionTimeMs={result.query_result.execution_time_ms}
              exportFilenamePrefix={`query_export_${turnId}`}
              enableSearch={true}
              enablePagination={true}
              defaultPageSize={25}
            />
          )}
        </div>
      )}

      {/* Tab 7: Pipeline Latency Trace */}
      {activeTab === "trace" && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-foreground pb-1 border-b border-border/50">
            Multi-Agent Execution Latency Trace
          </h4>
          <div className="space-y-1.5 font-mono text-xs">
            {result.trace_steps.map((step, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-background/50 border border-border flex items-center justify-between"
              >
                <div className="flex items-center gap-2.5">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      step.status === "succeeded" ? "bg-success" : "bg-destructive"
                    }`}
                  />
                  <span className="font-semibold text-foreground">{step.step}</span>
                  <span className="text-muted-foreground truncate max-w-[380px]">
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

      {/* Suggested Follow-up Questions Strip */}
      {result.suggested_followups && result.suggested_followups.length > 0 && (
        <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 space-y-2.5 pt-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-primary">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Suggested Next Questions (Click to Investigate):</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {result.suggested_followups.map((qText, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onSelectFollowUp(qText)}
                className="px-3.5 py-1.5 rounded-xl border border-border/80 bg-card hover:border-primary/80 hover:bg-muted/40 text-left text-xs text-foreground/90 hover:text-primary transition-all flex items-center gap-2 group cursor-pointer shadow-sm"
              >
                <span>{qText}</span>
                <ArrowRight className="w-3 h-3 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


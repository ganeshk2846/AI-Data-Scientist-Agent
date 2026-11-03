import React, { useState } from "react";
import {
  Sparkles,
  TrendingUp,
  HelpCircle,
  Compass,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Database,
  BarChart2,
  GitBranch,
  Layers,
  ChevronDown,
  ChevronUp,
  Clock,
  Code2,
} from "lucide-react";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { AgentTask, ManagementResponse, SupervisorExecutionResult } from "@/types/api";

export interface ManagementResponseViewProps {
  execution: SupervisorExecutionResult;
}

export function ManagementResponseView({ execution }: ManagementResponseViewProps) {
  const {
    execution_id,
    question,
    plan_summary,
    tasks = [],
    management_response,
    metrics = {},
    success,
    database_fingerprint,
  } = execution;

  const [showTasks, setShowTasks] = useState(true);
  const [showEvidence, setShowEvidence] = useState(false);

  const { what, why, what_next, so_what, executive_summary } = management_response || {};

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
            <CheckCircle2 className="w-3 h-3" />
            <span>Completed</span>
          </span>
        );
      case "ABSTAINED":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-500 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
            <AlertTriangle className="w-3 h-3" />
            <span>Abstained</span>
          </span>
        );
      case "FAILED":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-destructive bg-destructive/10 border border-destructive/20 px-2 py-0.5 rounded">
            <XCircle className="w-3 h-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono text-muted-foreground bg-muted/40 px-2 py-0.5 rounded">
            <Clock className="w-3 h-3" />
            <span>{status}</span>
          </span>
        );
    }
  };

  const getSpecialistColor = (specialist: string) => {
    switch (specialist) {
      case "DATA_RETRIEVAL":
        return "bg-blue-500/10 text-blue-500 border-blue-500/30";
      case "DIAGNOSTIC":
        return "bg-amber-500/10 text-amber-500 border-amber-500/30";
      case "PREDICTIVE":
        return "bg-purple-500/10 text-purple-500 border-purple-500/30";
      case "PRESCRIPTIVE":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/30";
      case "CRITIC":
        return "bg-indigo-500/10 text-indigo-500 border-indigo-500/30";
      default:
        return "bg-primary/10 text-primary border-primary/30";
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Execution Meta Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3 border-b border-border gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="primary" size="sm" className="font-semibold uppercase tracking-wider">
            Agentic Decision Support
          </Badge>
          <span className="text-xs text-foreground font-semibold">
            {plan_summary || "Multi-Agent Analytical Plan"}
          </span>
          <Badge variant="mono" size="xs">
            ID: {execution_id}
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground font-mono bg-muted/40 px-2 py-0.5 rounded border border-border/50">
            Latency: {metrics.latency_ms ? `${metrics.latency_ms}ms` : "0ms"}
          </span>
          <span className="text-muted-foreground font-mono bg-muted/40 px-2 py-0.5 rounded border border-border/50">
            Queries: {metrics.sql_queries ?? 0}
          </span>
          <span className="text-muted-foreground font-mono bg-muted/40 px-2 py-0.5 rounded border border-border/50">
            DB: {database_fingerprint ? database_fingerprint.slice(0, 8) : "default"}
          </span>
        </div>
      </div>

      {/* 2. Orchestration Specialist Task Pipeline Stepper */}
      <div className="p-4 rounded-xl border border-border bg-card/50 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-foreground flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary" />
            <span>Specialist Agent Task Pipeline ({tasks.length} Tasks)</span>
          </span>
          <button
            type="button"
            onClick={() => setShowTasks(!showTasks)}
            className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors cursor-pointer"
          >
            <span>{showTasks ? "Hide Details" : "Show Details"}</span>
            {showTasks ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {showTasks && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
            {tasks.map((task: AgentTask) => (
              <div
                key={task.task_id}
                className="p-3 rounded-lg border border-border/80 bg-background/60 space-y-1.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getSpecialistColor(
                      task.specialist
                    )}`}
                  >
                    {task.specialist.replace(/_/g, " ")}
                  </span>
                  {getStatusBadge(task.status)}
                </div>
                <div className="text-xs font-medium text-foreground truncate">
                  {task.task_type.replace(/_/g, " ")}
                </div>
                {task.output_summary && (
                  <p className="text-[11px] text-muted-foreground truncate">{task.output_summary}</p>
                )}
                {task.error_or_abstain_reason && task.status !== "COMPLETED" && (
                  <p className="text-[10px] text-amber-500/90 italic truncate">
                    Reason: {task.error_or_abstain_reason}
                  </p>
                )}
                <div className="flex items-center justify-between text-[10px] text-muted-foreground/80 font-mono pt-1 border-t border-border/40">
                  <span>Duration: {task.duration_ms.toFixed(1)}ms</span>
                  <span>{task.evidence_references?.length || 0} Evidence Refs</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3. Executive Decision Cards: WHAT, WHY, WHAT NEXT, SO WHAT */}
      <div className="space-y-4">
        {/* Card 1: WHAT (What happened?) */}
        {what && (
          <div className="p-5 rounded-2xl border border-blue-500/30 bg-blue-500/5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-500 font-bold text-xs uppercase tracking-wider">
                  WHAT
                </div>
                <h3 className="text-sm font-bold text-foreground">What happened?</h3>
              </div>
              <Badge variant="mono" size="xs">
                Descriptive Baseline
              </Badge>
            </div>
            <p className="text-xs font-semibold text-foreground/90">{what.headline}</p>
            <div className="text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed">
              {what.content}
            </div>

            {/* KPIs Grid */}
            {what.kpis && Object.keys(what.kpis).length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
                {Object.entries(what.kpis)
                  .filter(([_, v]) => typeof v === "number" || typeof v === "string")
                  .slice(0, 4)
                  .map(([k, v]) => (
                    <div key={k} className="p-2.5 rounded-lg border border-border/80 bg-card/60">
                      <span className="text-[9px] uppercase font-mono text-muted-foreground truncate block">
                        {k.replace(/_/g, " ")}
                      </span>
                      <p className="text-sm font-bold font-mono text-foreground truncate">
                        {typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(v)}
                      </p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Card 2: WHY (Why did it happen?) */}
        {why && (
          <div className="p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-500 font-bold text-xs uppercase tracking-wider">
                  WHY
                </div>
                <h3 className="text-sm font-bold text-foreground">Why did it happen?</h3>
              </div>
              <Badge variant="mono" size="xs">
                Diagnostic Analysis
              </Badge>
            </div>
            <p className="text-xs font-semibold text-foreground/90">{why.headline}</p>
            <div className="text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed">
              {why.content}
            </div>

            {/* Non-causal Disclaimer */}
            {why.disclaimers && why.disclaimers.length > 0 && (
              <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/10 text-[11px] text-amber-500/90 space-y-1">
                {why.disclaimers.map((disc, idx) => (
                  <p key={idx} className="italic leading-relaxed">
                    {disc}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Card 3: WHAT NEXT (What might happen?) */}
        {what_next && (
          <div className="p-5 rounded-2xl border border-purple-500/30 bg-purple-500/5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-500 font-bold text-xs uppercase tracking-wider">
                  WHAT NEXT
                </div>
                <h3 className="text-sm font-bold text-foreground">What might happen?</h3>
              </div>
              <Badge variant="mono" size="xs">
                Predictive Forecast
              </Badge>
            </div>
            <p className="text-xs font-semibold text-foreground/90">{what_next.headline}</p>
            <div className="text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed">
              {what_next.content}
            </div>

            {/* Forecast KPIs */}
            {what_next.kpis && Object.keys(what_next.kpis).length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
                {Object.entries(what_next.kpis)
                  .filter(([_, v]) => typeof v === "number" || typeof v === "string")
                  .slice(0, 4)
                  .map(([k, v]) => (
                    <div key={k} className="p-2.5 rounded-lg border border-border/80 bg-card/60">
                      <span className="text-[9px] uppercase font-mono text-muted-foreground truncate block">
                        {k.replace(/_/g, " ")}
                      </span>
                      <p className="text-sm font-bold font-mono text-foreground truncate">
                        {typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(v)}
                      </p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Card 4: SO WHAT (What should management do?) */}
        {so_what && (
          <div className="p-5 rounded-2xl border border-emerald-500/30 bg-emerald-500/5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-500 font-bold text-xs uppercase tracking-wider">
                  SO WHAT
                </div>
                <h3 className="text-sm font-bold text-foreground">What should management do?</h3>
              </div>
              <Badge variant="mono" size="xs">
                Prescriptive Action
              </Badge>
            </div>
            <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              {so_what.headline}
            </p>
            <div className="text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed">
              {so_what.content}
            </div>

            {/* Safe Advisory Disclaimer */}
            {so_what.disclaimers && so_what.disclaimers.length > 0 && (
              <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-[11px] text-emerald-600 dark:text-emerald-400 space-y-1">
                {so_what.disclaimers.map((disc, idx) => (
                  <p key={idx} className="italic leading-relaxed">
                    {disc}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 4. Grounding & Evidence Inspector Toggle */}
      <div className="p-4 rounded-xl border border-border bg-card/40 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-primary" />
            <span>Grounded Evidence & Query Provenance</span>
          </span>
          <Button
            variant="ghost"
            size="xs"
            onClick={() => setShowEvidence(!showEvidence)}
          >
            {showEvidence ? "Hide Evidence" : "Inspect Evidence"}
          </Button>
        </div>

        {showEvidence && (
          <div className="pt-2 space-y-2 text-xs">
            <div className="p-3 rounded-lg bg-background/80 border border-border space-y-1 font-mono text-[11px]">
              <span className="text-muted-foreground uppercase text-[10px] block">
                Executed SQL Queries:
              </span>
              {execution.analytical_result?.executed_queries?.length ? (
                execution.analytical_result.executed_queries.map((q, idx) => (
                  <pre key={idx} className="overflow-x-auto text-primary whitespace-pre-wrap">
                    {q}
                  </pre>
                ))
              ) : (
                <span className="text-muted-foreground italic">No queries executed.</span>
              )}
            </div>

            {execution.analytical_result?.faithfulness?.structured_claims?.length ? (
              <div className="p-3 rounded-lg bg-background/80 border border-border space-y-1">
                <span className="text-muted-foreground uppercase text-[10px] font-mono block">
                  Critic Verified Claims:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px]">
                  {execution.analytical_result.faithfulness.structured_claims.map((claim) => (
                    <div
                      key={claim.claim_id}
                      className="p-1.5 rounded border border-border/60 flex items-center gap-1.5 text-foreground/80"
                    >
                      {claim.verified ? (
                        <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
                      )}
                      <span className="truncate">{claim.statement}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

import React from "react";
import { Check, RefreshCw } from "lucide-react";

export const WORKFLOW_STEPS = [
  { key: "understanding_question", label: "Router & Gate", desc: "Intent & safety triage" },
  { key: "retrieving_schema", label: "Schema Grounder", desc: "BM25 + TF-IDF RRF" },
  { key: "generating_query", label: "SQL Generator", desc: "Candidate SELECT" },
  { key: "validating_query", label: "AST Guardrail", desc: "sqlglot AST & repair" },
  { key: "running_query", label: "Read-Only Runner", desc: "SQLite execution" },
  { key: "verifying_results", label: "Verifier & Spec", desc: "Bounds & chart spec" },
  { key: "composing_answer", label: "Executive Composer", desc: "Synthesis & follow-ups" },
];

export interface StreamingStepperProps {
  activeStepKey?: string;
  activeStepMessage?: string;
  completedSteps?: string[];
}

export function StreamingStepper({
  activeStepKey,
  activeStepMessage,
  completedSteps = [],
}: StreamingStepperProps) {
  return (
    <div className="p-5 rounded-xl border border-primary/40 bg-card/90 backdrop-blur shadow-md space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs gap-2 pb-1 border-b border-border/50">
        <div className="flex items-center gap-2 text-primary font-medium">
          <RefreshCw className="w-4 h-4 animate-spin text-primary" />
          <span className="font-semibold text-foreground">Multi-Agent DAG Execution in Progress...</span>
        </div>
        <span className="text-[11px] font-mono text-muted-foreground bg-muted/60 px-2 py-0.5 rounded border border-border/60">
          {activeStepMessage || "Processing workflow pipeline..."}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 text-xs">
        {WORKFLOW_STEPS.map((s, idx) => {
          const isDone = completedSteps.includes(s.key);
          const isCurrent = activeStepKey === s.key;

          return (
            <div
              key={s.key}
              className={`p-2.5 rounded-lg border flex flex-col justify-between transition-all duration-200 ${
                isDone
                  ? "border-success/50 bg-success/10 text-success"
                  : isCurrent
                  ? "border-primary bg-primary/15 text-primary shadow-sm ring-1 ring-primary/30"
                  : "border-border/60 bg-background/40 text-muted-foreground"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono font-semibold opacity-70">
                  0{idx + 1}
                </span>
                {isDone ? (
                  <Check className="w-3.5 h-3.5 text-success stroke-[2.5]" />
                ) : isCurrent ? (
                  <RefreshCw className="w-3.5 h-3.5 text-primary animate-spin" />
                ) : null}
              </div>
              <div>
                <span className="text-[11px] font-medium leading-tight block truncate text-foreground/90">
                  {s.label}
                </span>
                <span className="text-[9px] text-muted-foreground block truncate">
                  {s.desc}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}


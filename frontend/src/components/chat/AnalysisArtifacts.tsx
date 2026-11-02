import React from "react";
import {
  Sparkles,
  AlertTriangle,
  TrendingUp,
  Users,
  DollarSign,
  Calendar,
  Target,
  ShieldCheck,
  Compass,
  CheckCircle2,
  HelpCircle,
  BarChart2,
} from "lucide-react";
import { Badge } from "../ui/Badge";

export interface AnalysisArtifactsProps {
  analysis: any;
}

export function AnalysisArtifacts({ analysis }: AnalysisArtifactsProps) {
  // Check if this is a Phase 4 StandardizedAnalyticalResult
  if (analysis.analytical_type && analysis.selected_methods) {
    const {
      analysis_id,
      analytical_type,
      analysis_question,
      selected_methods,
      computed_metrics = {},
      result_data = [],
      faithfulness,
      confidence_score = 1.0,
      uncertainty_notes = [],
      findings = [],
      limitations = [],
      recommended_next_steps = [],
    } = analysis;

    const intentColor = {
      DESCRIPTIVE: "bg-blue-500/10 text-blue-500 border-blue-500/30",
      DIAGNOSTIC: "bg-amber-500/10 text-amber-500 border-amber-500/30",
      PREDICTIVE: "bg-purple-500/10 text-purple-500 border-purple-500/30",
      PRESCRIPTIVE: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30",
      SQL_LOOKUP: "bg-muted text-muted-foreground border-border",
    }[analytical_type as string] || "bg-primary/10 text-primary border-primary/30";

    return (
      <div className="space-y-5">
        {/* Phase 4 Header Strip */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs pb-3 border-b border-border gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <div className={`p-1.5 rounded-lg border font-semibold uppercase text-[11px] tracking-wider px-2.5 py-1 ${intentColor}`}>
              {analytical_type}
            </div>
            <span className="font-semibold text-foreground text-sm">
              Method: {selected_methods.join(", ").replace(/_/g, " ")}
            </span>
            <Badge variant="mono" size="xs">
              ID: {analysis_id}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {faithfulness && faithfulness.is_faithful ? (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Faithfulness Verified</span>
              </span>
            ) : (
              <span className="text-[11px] text-muted-foreground font-mono bg-muted/40 px-2 py-0.5 rounded">
                Confidence: {(confidence_score * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>

        {/* 1. Key Metrics Cards Grid */}
        {Object.keys(computed_metrics).length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(computed_metrics)
              .filter(([k, v]) => typeof v === "number" || typeof v === "string")
              .slice(0, 8)
              .map(([key, val]) => (
                <div key={key} className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
                  <span className="text-[10px] text-muted-foreground uppercase font-mono tracking-wider truncate block">
                    {key.replace(/_/g, " ")}
                  </span>
                  <p className="text-lg font-bold font-mono text-foreground truncate">
                    {typeof val === "number" ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(val)}
                  </p>
                </div>
              ))}
          </div>
        )}

        {/* 1.5 Structured Claim Evidence Bindings */}
        {faithfulness?.structured_claims && faithfulness.structured_claims.length > 0 && (
          <div className="p-3.5 rounded-xl border border-border bg-card/40 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                <span>Evidence-Linked Claims ({faithfulness.verified_claims}/{faithfulness.total_claims_checked} Verified)</span>
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                Faithfulness: {faithfulness.is_faithful ? "100%" : `${Math.round((faithfulness.verified_claims / Math.max(faithfulness.total_claims_checked, 1)) * 100)}%`}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
              {faithfulness.structured_claims.slice(0, 6).map((c: any) => (
                <div
                  key={c.claim_id}
                  className={`p-2 rounded-lg border flex items-start gap-1.5 ${
                    c.verified
                      ? "border-emerald-500/20 bg-emerald-500/5 text-foreground/90"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-500"
                  }`}
                >
                  {c.verified ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-0.5 truncate">
                    <p className="font-medium truncate">{c.statement}</p>
                    <p className="text-[10px] text-muted-foreground font-mono truncate">
                      {c.verified ? `Ref: ${c.evidence_reference || "computed"}` : `Issue: ${c.discrepancy}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 2. Structured Findings Narrative */}
        {findings.length > 0 && (
          <div className="p-4 rounded-xl border border-border bg-muted/20 space-y-2">
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              <span>Evidence-Backed Findings</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-foreground/90 list-disc list-inside">
              {findings.map((f: string, i: number) => (
                <li key={i} className="leading-relaxed">{f}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 3. Predictive / Diagnostic / Prescriptive Result Data Table */}
        {result_data.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
              <BarChart2 className="w-3.5 h-3.5 text-primary" />
              <span>Analytical Records & Projections ({result_data.length})</span>
            </h4>
            <div className="overflow-x-auto rounded-xl border border-border bg-card/40 max-h-60 overflow-y-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-muted/70 text-muted-foreground font-semibold border-b border-border sticky top-0">
                  <tr>
                    {Object.keys(result_data[0]).slice(0, 7).map((col) => (
                      <th key={col} className="p-2.5 font-mono capitalize">{col.replace(/_/g, " ")}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {result_data.slice(0, 15).map((row: any, rIdx: number) => (
                    <tr key={rIdx} className="hover:bg-muted/30 transition-colors">
                      {Object.keys(result_data[0]).slice(0, 7).map((col) => (
                        <td key={col} className="p-2.5 font-mono text-foreground/85">
                          {typeof row[col] === "number"
                            ? row[col].toLocaleString(undefined, { maximumFractionDigits: 2 })
                            : String(row[col] ?? "-")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 4. Actionable Prescriptive Recommendations */}
        {recommended_next_steps.length > 0 && (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-2">
            <h4 className="text-xs font-semibold text-emerald-500 uppercase tracking-wider flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5" />
              <span>Recommended Next Steps & Prescriptions</span>
            </h4>
            <ul className="space-y-1.5 text-xs text-foreground/90 list-disc list-inside">
              {recommended_next_steps.map((rec: string, i: number) => (
                <li key={i} className="leading-relaxed font-medium">{rec}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 5. Uncertainty & Disclaimers */}
        {uncertainty_notes.length > 0 && (
          <div className="flex items-start gap-2 p-3 rounded-lg border border-border/60 bg-muted/30 text-[11px] text-muted-foreground">
            <HelpCircle className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              {uncertainty_notes.map((note: string, i: number) => (
                <p key={i}>{note}</p>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Fallback: Legacy V1 AnalysisToolResult
  const { tool_name = "analysis", provenance = {}, churn_risk, anomaly_detection, forecast, optimization } = analysis;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs pb-3 border-b border-border gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="p-1.5 rounded-lg bg-primary/20 text-primary">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="font-semibold text-foreground text-sm capitalize">
            {tool_name.replace(/_/g, " ")}
          </span>
          <Badge variant="primary" size="xs">
            Algorithm: {provenance.method_name || "deterministic"}
          </Badge>
          <Badge variant="mono" size="xs">
            Dataset: {provenance.source_dataset || "active_database"}
          </Badge>
        </div>
        <span className="text-[11px] text-muted-foreground font-mono bg-muted/40 px-2.5 py-1 rounded border border-border/50">
          Window: {provenance.time_window || "dynamic"}
        </span>
      </div>

      {churn_risk && (
        <div className="p-4 rounded-xl border border-border bg-card/40 space-y-2">
          <p className="text-xs text-muted-foreground">Total Analyzed: {churn_risk.total_customers_analyzed}</p>
          <p className="text-base font-bold text-destructive">Revenue at Risk: ${churn_risk.total_revenue_at_risk?.toLocaleString()}</p>
        </div>
      )}
    </div>
  );
}

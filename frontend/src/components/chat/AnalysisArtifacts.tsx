import React from "react";
import { Sparkles, AlertTriangle, TrendingUp, Users, DollarSign, Calendar, Target } from "lucide-react";
import { AnalysisToolResult } from "@/types/api";
import { Badge } from "../ui/Badge";

export interface AnalysisArtifactsProps {
  analysis: AnalysisToolResult;
}

export function AnalysisArtifacts({ analysis }: AnalysisArtifactsProps) {
  const { tool_name, provenance, churn_risk, anomaly_detection, forecast, optimization } = analysis;

  return (
    <div className="space-y-4">
      {/* Tool Header Strip */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs pb-3 border-b border-border gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="p-1.5 rounded-lg bg-primary/20 text-primary">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="font-semibold text-foreground text-sm capitalize">
            {tool_name.replace(/_/g, " ")}
          </span>
          <Badge variant="primary" size="xs">
            Algorithm: {provenance.method_name}
          </Badge>
          <Badge variant="mono" size="xs">
            Dataset: {provenance.source_dataset}
          </Badge>
        </div>
        <span className="text-[11px] text-muted-foreground font-mono bg-muted/40 px-2.5 py-1 rounded border border-border/50">
          Window: {provenance.time_window}
        </span>
      </div>

      {/* 1. Customer Churn Risk Artifact */}
      {churn_risk && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                <Users className="w-3.5 h-3.5 text-primary" />
                <span>Customers Analyzed</span>
              </span>
              <p className="text-xl font-bold font-mono text-foreground">
                {churn_risk.total_customers_analyzed.toLocaleString()}
              </p>
            </div>
            <div className="p-3.5 rounded-xl border border-destructive/30 bg-destructive/10 space-y-1">
              <span className="text-[11px] text-destructive font-medium flex items-center gap-1">
                <DollarSign className="w-3.5 h-3.5 text-destructive" />
                <span>Revenue at Risk</span>
              </span>
              <p className="text-xl font-bold font-mono text-destructive">
                ${churn_risk.total_revenue_at_risk.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </p>
            </div>
            <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
              <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-warning" />
                <span>Inactivity Threshold</span>
              </span>
              <p className="text-xl font-bold font-mono text-foreground">
                {churn_risk.inactivity_threshold_days} Days
              </p>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-border bg-card/40">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-muted/70 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="p-3 font-mono">Rank</th>
                  <th className="p-3">Customer Segment</th>
                  <th className="p-3 font-mono">Customers</th>
                  <th className="p-3 font-mono">Churn Rate (Wilson 95% CI)</th>
                  <th className="p-3 font-mono">Historical Spend</th>
                  <th className="p-3 font-mono">Revenue at Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {churn_risk.segments.map((seg) => (
                  <tr key={seg.segment_name} className="hover:bg-muted/30 transition-colors">
                    <td className="p-3 font-bold font-mono text-primary">#{seg.actionability_rank}</td>
                    <td className="p-3 font-semibold text-foreground">{seg.segment_name}</td>
                    <td className="p-3 font-mono text-foreground/80">{seg.customer_count.toLocaleString()}</td>
                    <td className="p-3 font-mono">
                      <span className="font-semibold text-warning">{seg.churn_rate_pct}%</span>
                      <span className="text-[10px] text-muted-foreground ml-1.5 font-normal">
                        ({seg.confidence_interval_low}% – {seg.confidence_interval_high}%)
                      </span>
                    </td>
                    <td className="p-3 font-mono text-foreground/90">
                      ${seg.total_historical_spend.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="p-3 font-mono font-semibold text-destructive">
                      ${seg.revenue_at_risk.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 2. Anomaly Detection Artifact */}
      {anomaly_detection && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 rounded-xl border border-border bg-card/60 text-xs">
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground">
                Anomalies detected:{" "}
                <strong className="text-foreground text-sm font-mono">
                  {anomaly_detection.anomaly_count}
                </strong>{" "}
                of {anomaly_detection.total_data_points} points
              </span>
              <Badge variant="warning" size="xs">
                Threshold: |z| ≥ {anomaly_detection.threshold}
              </Badge>
            </div>
            <span className="text-muted-foreground font-mono text-[11px]">
              Method: {anomaly_detection.method}
            </span>
          </div>

          {anomaly_detection.anomalies.filter((a) => a.is_anomaly).length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-border bg-card/40">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-muted/70 text-muted-foreground font-semibold border-b border-border">
                  <tr>
                    <th className="p-3 font-mono">Date</th>
                    <th className="p-3 font-mono">Actual Value</th>
                    <th className="p-3 font-mono">Expected Baseline</th>
                    <th className="p-3 font-mono">Z-Score</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Quality Screen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {anomaly_detection.anomalies
                    .filter((a) => a.is_anomaly)
                    .map((anom, idx) => (
                      <tr key={idx} className="hover:bg-muted/30 transition-colors">
                        <td className="p-3 font-mono font-medium text-foreground">{anom.date}</td>
                        <td className="p-3 font-mono font-bold text-foreground">
                          {anom.actual_value.toLocaleString()}
                        </td>
                        <td className="p-3 font-mono text-muted-foreground">
                          {anom.expected_value.toLocaleString()}
                        </td>
                        <td className="p-3 font-mono text-warning font-semibold">{anom.z_score}</td>
                        <td className="p-3">
                          <Badge
                            variant={anom.severity === "severe" ? "destructive" : "warning"}
                            size="xs"
                          >
                            {anom.severity.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="p-3 font-mono text-[11px]">
                          {anom.quality_flag ? (
                            <span className="text-destructive font-semibold">{anom.quality_flag}</span>
                          ) : (
                            <span className="text-success font-medium">Passed</span>
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

      {/* 3. Time-Series Forecasting Artifact */}
      {forecast && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-0.5">
              <span className="text-[11px] text-muted-foreground">Forecasting Algorithm</span>
              <p className="font-semibold text-sm text-foreground">{forecast.model_used}</p>
            </div>
            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-0.5">
              <span className="text-[11px] text-muted-foreground">Backtest MAE</span>
              <p className="font-semibold text-sm font-mono text-foreground">
                {forecast.backtest_mae !== null && forecast.backtest_mae !== undefined
                  ? forecast.backtest_mae.toFixed(2)
                  : "N/A"}
              </p>
            </div>
            <div className="p-3 rounded-xl border border-border bg-card/60 space-y-0.5">
              <span className="text-[11px] text-muted-foreground">Backtest MAPE Error</span>
              <p className="font-semibold text-sm font-mono text-foreground">
                {forecast.backtest_mape_pct !== null && forecast.backtest_mape_pct !== undefined
                  ? `${forecast.backtest_mape_pct.toFixed(2)}%`
                  : "N/A"}
              </p>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-border bg-card/40">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-muted/70 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="p-3 font-mono">Forecast Horizon Date</th>
                  <th className="p-3 font-mono">Point Forecast</th>
                  <th className="p-3 font-mono">80% Prediction Interval</th>
                  <th className="p-3 font-mono">95% Prediction Interval</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {forecast.points.map((pt) => (
                  <tr key={pt.date} className="hover:bg-muted/30 transition-colors">
                    <td className="p-3 font-mono font-medium text-foreground">{pt.date}</td>
                    <td className="p-3 font-mono font-bold text-primary">
                      {pt.point_forecast.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="p-3 font-mono text-muted-foreground">
                      [{pt.lower_bound_80.toFixed(1)} – {pt.upper_bound_80.toFixed(1)}]
                    </td>
                    <td className="p-3 font-mono text-muted-foreground">
                      [{pt.lower_bound_95.toFixed(1)} – {pt.upper_bound_95.toFixed(1)}]
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 4. SLSQP Prescriptive Optimization Artifact */}
      {optimization && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-border bg-card/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <span className="text-xs text-muted-foreground">Total Budget Allocated</span>
              <p className="text-xl font-bold font-mono text-foreground">
                ${optimization.total_budget.toLocaleString()}
              </p>
            </div>
            <div>
              <span className="text-xs text-muted-foreground">Simulated Expected Return</span>
              <p className="text-xl font-bold font-mono text-success">
                ${optimization.expected_total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </p>
            </div>
            <Badge variant={optimization.constraints_satisfied ? "success" : "warning"}>
              {optimization.constraints_satisfied ? "Constraints Satisfied" : "Unconstrained"}
            </Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {Object.entries(optimization.allocations).map(([ch, alloc]) => (
              <div
                key={ch}
                className="p-3 rounded-xl border border-border/80 bg-background/50 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <Target className="w-3.5 h-3.5 text-primary" />
                  <span className="font-semibold text-foreground">{ch}</span>
                </div>
                <span className="font-mono font-bold text-primary">
                  ${alloc.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


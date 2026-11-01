"use client";

import { AlertCircle, CheckCircle2, Database, KeyRound, RefreshCw, Server, ShieldCheck } from "lucide-react";
import { ReadinessStatus } from "@/types/api";

interface HealthReadinessCardProps {
  data?: ReadinessStatus;
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  onRefresh: () => void;
}

export function HealthReadinessCard({
  data,
  isLoading,
  isError,
  error,
  onRefresh,
}: HealthReadinessCardProps) {
  if (isLoading) {
    return (
      <div className="p-8 rounded-xl border border-border bg-card shadow-sm flex flex-col items-center justify-center space-y-4">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        <div className="text-center">
          <h3 className="font-medium text-foreground">Probing Backend Services...</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Verifying SQLite read-only connection and schema integrity
          </p>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-8 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive shadow-sm">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-6 h-6 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-base">Backend Connection Offline</h3>
            <p className="text-xs text-muted-foreground mt-1 text-foreground/80">
              {error?.message || "Could not connect to FastAPI backend at http://localhost:8001"}
            </p>
            <div className="mt-4 p-3 rounded-lg bg-background/50 border border-border font-mono text-xs text-muted-foreground">
              Run backend: <code>python -m uvicorn backend.app.main:app --port 8001 --reload</code>
            </div>
            <button
              onClick={onRefresh}
              className="mt-4 px-4 py-2 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 flex items-center space-x-2"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Connection</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { database, llm, app_store_ready, ready } = data;

  return (
    <div className="p-6 rounded-xl border border-border bg-card space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-base font-semibold text-foreground">System Readiness & Architecture</h2>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                ready
                  ? "bg-success/20 text-success border border-success/30"
                  : "bg-warning/20 text-warning border border-warning/30"
              }`}
            >
              {ready ? "Phase 1 Foundation Active" : "Action Required"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Runtime verification of read-only dataset, LLM provider, and agent persistence store
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="p-2 rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh Readiness Probe"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Database Card */}
        <div className="p-4 rounded-lg border border-border bg-background/40 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-primary font-medium text-sm">
              <Database className="w-4 h-4" />
              <span>Business Warehouse</span>
            </div>
            {database.connected && database.read_only_verified ? (
              <span className="flex items-center space-x-1 text-xs text-success">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Read-Only Verified</span>
              </span>
            ) : (
              <span className="text-xs text-destructive">Error</span>
            )}
          </div>

          <div className="space-y-1.5 text-xs text-muted-foreground">
            <div className="flex justify-between">
              <span>Path:</span>
              <span className="font-mono text-foreground text-right truncate max-w-[160px]" title={database.path}>
                {database.path.split(/[/\\]/).pop()}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Cataloged Tables:</span>
              <span className="font-semibold text-foreground">{database.table_count ?? "N/A"}</span>
            </div>
            <div className="flex justify-between">
              <span>Verified Rows:</span>
              <span className="font-semibold text-foreground">
                {database.total_rows?.toLocaleString() ?? "N/A"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Database Size:</span>
              <span className="font-mono text-foreground">
                {database.size_bytes ? `${(database.size_bytes / (1024 * 1024)).toFixed(1)} MB` : "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* LLM Provider Card */}
        <div className="p-4 rounded-lg border border-border bg-background/40 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-primary font-medium text-sm">
              <KeyRound className="w-4 h-4" />
              <span>LLM Synthesis</span>
            </div>
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                llm.configured
                  ? "bg-success/20 text-success"
                  : "bg-warning/20 text-warning"
              }`}
            >
              {llm.configured ? "Ready" : "Offline / Mock"}
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-muted-foreground">
            <div className="flex justify-between">
              <span>Provider:</span>
              <span className="font-mono text-foreground capitalize">{llm.provider}</span>
            </div>
            <div className="flex justify-between">
              <span>Target Model:</span>
              <span className="font-mono text-foreground">{llm.model}</span>
            </div>
            <p className="text-[11px] text-muted-foreground pt-1 border-t border-border/50">
              {llm.message}
            </p>
          </div>
        </div>

        {/* Agent Store Card */}
        <div className="p-4 rounded-lg border border-border bg-background/40 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-primary font-medium text-sm">
              <Server className="w-4 h-4" />
              <span>Agent Checkpoints</span>
            </div>
            <span className="text-xs text-success flex items-center space-x-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Isolated</span>
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-muted-foreground">
            <div className="flex justify-between">
              <span>Target Store:</span>
              <span className="font-mono text-foreground">agent_app.sqlite</span>
            </div>
            <div className="flex justify-between">
              <span>Directory State:</span>
              <span className="text-success font-medium">Ready</span>
            </div>
            <p className="text-[11px] text-muted-foreground pt-1 border-t border-border/50">
              LangGraph local SQLite checkpoints & traces remain isolated from business data.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}


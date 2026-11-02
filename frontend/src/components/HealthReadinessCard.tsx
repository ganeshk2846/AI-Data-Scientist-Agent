"use client";

import React from "react";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  KeyRound,
  RefreshCw,
  Server,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import { ReadinessStatus } from "@/types/api";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";

export interface HealthReadinessCardProps {
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
      <div className="p-8 rounded-2xl border border-border/80 bg-card/90 shadow-md flex flex-col items-center justify-center space-y-3">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
        <div className="text-center">
          <h3 className="font-semibold text-sm text-foreground">Probing Backend Services...</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Verifying SQLite read-only immutability and schema integrity
          </p>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 rounded-2xl border border-destructive/40 bg-destructive/10 text-destructive shadow-lg space-y-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-destructive/20 text-destructive flex-shrink-0">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="flex-1 space-y-1">
            <h3 className="font-bold text-base">Backend Connection Offline</h3>
            <p className="text-xs text-foreground/80 leading-relaxed">
              {error?.message || "Could not connect to FastAPI backend at http://localhost:8001"}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-background/80 border border-border space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
            <Terminal className="w-4 h-4 text-primary" />
            <span>Start Backend Service:</span>
          </div>
          <pre className="p-2.5 rounded-lg bg-card text-xs font-mono text-primary border border-border/60 overflow-x-auto">
            <code>python -m uvicorn backend.app.main:app --port 8001 --reload</code>
          </pre>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={onRefresh}
          icon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          Retry Connection
        </Button>
      </div>
    );
  }

  const { database, llm, app_store_ready, ready } = data;

  return (
    <div className="p-6 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-border/80 gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold text-foreground">System Readiness & Architecture</h2>
            <Badge variant={ready ? "success" : "warning"} size="sm">
              {ready ? "Production Ready" : "Attention Required"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Runtime verification of read-only dataset, LLM provider, and agent persistence store
          </p>
        </div>

        <Button
          variant="outline"
          size="xs"
          onClick={onRefresh}
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          title="Refresh Readiness Probe"
        >
          Refresh Probe
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Database Card */}
        <div className="p-4 rounded-xl border border-border bg-background/50 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <Database className="w-4 h-4" />
              <span>Business Warehouse</span>
            </div>
            {database.connected && database.read_only_verified ? (
              <Badge variant="success" size="xs" className="gap-1">
                <ShieldCheck className="w-3 h-3" />
                <span>Read-Only</span>
              </Badge>
            ) : (
              <Badge variant="destructive" size="xs">
                Error
              </Badge>
            )}
          </div>

          <div className="space-y-1.5 text-xs text-muted-foreground font-mono">
            <div className="flex justify-between">
              <span>Database File:</span>
              <span className="font-semibold text-foreground truncate max-w-[150px]" title={database.path}>
                {database.path.split(/[/\\]/).pop()}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Cataloged Tables:</span>
              <span className="font-semibold text-foreground">{database.table_count ?? "N/A"}</span>
            </div>
            <div className="flex justify-between">
              <span>Verified Records:</span>
              <span className="font-semibold text-foreground">
                {database.total_rows?.toLocaleString() ?? "N/A"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Database Size:</span>
              <span className="text-foreground">
                {database.size_bytes ? `${(database.size_bytes / (1024 * 1024)).toFixed(1)} MB` : "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* LLM Provider Card */}
        <div className="p-4 rounded-xl border border-border bg-background/50 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <KeyRound className="w-4 h-4" />
              <span>LLM Synthesis</span>
            </div>
            <Badge variant={llm.configured ? "success" : "warning"} size="xs">
              {llm.configured ? "Ready" : "Offline / Mock"}
            </Badge>
          </div>

          <div className="space-y-1.5 text-xs text-muted-foreground font-mono">
            <div className="flex justify-between">
              <span>Provider:</span>
              <span className="font-semibold text-foreground capitalize">{llm.provider}</span>
            </div>
            <div className="flex justify-between">
              <span>Active Model:</span>
              <span className="font-semibold text-foreground truncate max-w-[160px]">{llm.model}</span>
            </div>
            <p className="text-[11px] text-muted-foreground font-sans pt-1 border-t border-border/50 leading-relaxed">
              {llm.message}
            </p>
          </div>
        </div>

        {/* Agent Store Card */}
        <div className="p-4 rounded-xl border border-border bg-background/50 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <Server className="w-4 h-4" />
              <span>Agent Checkpoints</span>
            </div>
            <Badge variant={app_store_ready ? "success" : "warning"} size="xs" className="gap-1">
              <CheckCircle2 className="w-3 h-3" />
              <span>Isolated</span>
            </Badge>
          </div>

          <div className="space-y-1.5 text-xs text-muted-foreground font-mono">
            <div className="flex justify-between">
              <span>Target Store:</span>
              <span className="font-semibold text-foreground">agent_app.sqlite</span>
            </div>
            <div className="flex justify-between">
              <span>Directory State:</span>
              <span className="text-success font-medium">Ready</span>
            </div>
            <p className="text-[11px] text-muted-foreground font-sans pt-1 border-t border-border/50 leading-relaxed">
              LangGraph local SQLite memory frames, turns, and run telemetry remain strictly isolated from business data.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPreparationJob, fetchSchemaStatus, retryPreparationJob } from "@/lib/api";
import { PreparationJobState, PreparationStageInfo } from "@/types/api";
import {
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Clock,
  Sparkles,
  ArrowRight,
  Database,
  Search,
  Cpu,
  Layers,
  ShieldCheck,
  Binary,
  FileCode,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

interface PreparationProgressProps {
  initialJobId?: string;
  onComplete?: () => void;
}

const DEFAULT_STAGES = [
  { id: 1, name: "Database connection verified", icon: ShieldCheck },
  { id: 2, name: "Schema discovery", icon: Search },
  { id: 3, name: "Table profiling", icon: Database },
  { id: 4, name: "Semantic metadata construction", icon: FileCode },
  { id: 5, name: "Building dense vector index", icon: Binary },
  { id: 6, name: "Building BM25 index", icon: Layers },
  { id: 7, name: "Final preparation verification", icon: CheckCircle2 },
];

export function PreparationProgress({
  initialJobId,
  onComplete,
}: PreparationProgressProps) {
  const queryClient = useQueryClient();
  const [activeJobId, setActiveJobId] = useState<string | null>(initialJobId || null);
  const [startTime] = useState<number>(Date.now());
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  // Timer ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [startTime]);

  // Query latest job or schema status
  const { data: schemaStatusData } = useQuery({
    queryKey: ["schemaStatus"],
    queryFn: fetchSchemaStatus,
    refetchInterval: (query) => {
      const job = query.state.data?.latest_job;
      if (job?.status === "running" || job?.status === "pending") {
        return 1000;
      }
      return 5000;
    },
  });

  const latestJob: PreparationJobState | undefined =
    schemaStatusData?.latest_job as PreparationJobState | undefined;

  useEffect(() => {
    if (latestJob?.job_id && !activeJobId) {
      setActiveJobId(latestJob.job_id);
    }
  }, [latestJob?.job_id, activeJobId]);

  // Specific job poll if activeJobId exists
  const { data: jobData, refetch: refetchJob } = useQuery({
    queryKey: ["preparationJob", activeJobId],
    queryFn: () => (activeJobId ? fetchPreparationJob(activeJobId) : Promise.reject()),
    enabled: Boolean(activeJobId && activeJobId !== "cached_fingerprint"),
    refetchInterval: (query) => {
      const job = query.state.data;
      if (job?.status === "running" || job?.status === "pending") {
        return 1000;
      }
      return false;
    },
  });

  const currentJob = jobData || latestJob;
  const isSucceeded = currentJob?.status === "succeeded";
  const isFailed = currentJob?.status === "failed";
  const isRunning = currentJob?.status === "running" || currentJob?.status === "pending";

  // Retry mutation
  const retryMutation = useMutation({
    mutationFn: retryPreparationJob,
    onSuccess: (newJob) => {
      setActiveJobId(newJob.job_id);
      queryClient.invalidateQueries({ queryKey: ["schemaStatus"] });
      queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
      refetchJob();
    },
  });

  // Automatically notify parent when completed
  useEffect(() => {
    if (isSucceeded && onComplete) {
      const timer = setTimeout(() => {
        onComplete();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [isSucceeded, onComplete]);

  const stages: PreparationStageInfo[] = currentJob?.stages || [];
  const percent = currentJob?.progress_percent ?? (isSucceeded ? 100 : 15);

  return (
    <div className="bg-card border border-border/80 rounded-2xl p-6 sm:p-8 max-w-2xl mx-auto shadow-lg space-y-6">
      {/* Header */}
      <div className="space-y-1.5 text-center sm:text-left">
        <div className="flex items-center gap-2 justify-center sm:justify-start">
          <Badge variant="primary" size="xs" className="font-mono">
            7-STAGE PIPELINE
          </Badge>
          {isSucceeded && (
            <Badge variant="success" size="xs">
              COMPLETED
            </Badge>
          )}
          {isRunning && (
            <Badge variant="mono" size="xs" className="text-primary border-primary/30">
              <RefreshCw className="w-3 h-3 animate-spin mr-1" />
              RUNNING
            </Badge>
          )}
        </div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Preparing Your Database for AI Analysis
        </h2>
        <p className="text-xs text-muted-foreground">
          Your database is connected. We are discovering its structure, computing profiling metrics, and building high-performance retrieval indexes.
        </p>
      </div>

      {/* Progress Bar & Key Metrics */}
      <div className="space-y-3 bg-background/60 p-4 rounded-xl border border-border/60">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-foreground">
            {currentJob?.message || "Running preparation..."}
          </span>
          <span className="font-mono font-bold text-primary">{percent}%</span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-border/40 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 rounded-full ${
              isFailed
                ? "bg-destructive"
                : isSucceeded
                ? "bg-success"
                : "bg-primary"
            }`}
            style={{ width: `${Math.min(100, Math.max(5, percent))}%` }}
          />
        </div>

        <div className="grid grid-cols-3 gap-2 text-xs pt-1">
          <div className="p-2 rounded-lg bg-card/80 border border-border/50 text-center">
            <span className="text-[10px] text-muted-foreground block">TABLES PROCESSED</span>
            <span className="font-mono font-semibold text-foreground">
              {currentJob?.tables_processed || 0} / {currentJob?.total_tables || "--"}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-card/80 border border-border/50 text-center">
            <span className="text-[10px] text-muted-foreground block">ELAPSED TIME</span>
            <span className="font-mono font-semibold text-foreground">
              {elapsedSeconds}s
            </span>
          </div>
          <div className="p-2 rounded-lg bg-card/80 border border-border/50 text-center">
            <span className="text-[10px] text-muted-foreground block">STATUS</span>
            <span className={`font-mono font-semibold uppercase ${
              isSucceeded ? "text-success" : isFailed ? "text-destructive" : "text-primary"
            }`}>
              {currentJob?.status || "Running"}
            </span>
          </div>
        </div>
      </div>

      {/* 7-Stage Detailed Stepper */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Preparation Stages
        </h3>

        <div className="space-y-2">
          {DEFAULT_STAGES.map((def) => {
            const stageInfo = stages.find((s) => s.id === def.id);
            const status = stageInfo?.status || (isSucceeded ? "completed" : "waiting");
            const Icon = def.icon;

            return (
              <div
                key={def.id}
                className={`p-3 rounded-xl border flex items-center justify-between text-xs transition-colors ${
                  status === "completed"
                    ? "bg-success/5 border-success/30"
                    : status === "running"
                    ? "bg-primary/5 border-primary/40 shadow-sm"
                    : status === "failed"
                    ? "bg-destructive/10 border-destructive/40"
                    : "bg-background/40 border-border/50 opacity-60"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                      status === "completed"
                        ? "bg-success/20 text-success"
                        : status === "running"
                        ? "bg-primary/20 text-primary animate-pulse"
                        : status === "failed"
                        ? "bg-destructive/20 text-destructive"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {status === "completed" ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : status === "running" ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : status === "failed" ? (
                      <AlertCircle className="w-4 h-4" />
                    ) : (
                      <Clock className="w-4 h-4" />
                    )}
                  </div>

                  <div>
                    <span className="font-semibold text-foreground block">
                      Stage {def.id}: {def.name}
                    </span>
                    {stageInfo?.details && (
                      <span className="text-[11px] text-muted-foreground block truncate max-w-sm">
                        {stageInfo.details}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 font-mono text-[11px]">
                  {stageInfo?.elapsed_ms !== undefined && stageInfo.elapsed_ms !== null && (
                    <span className="text-muted-foreground">
                      {stageInfo.elapsed_ms.toFixed(1)}ms
                    </span>
                  )}
                  <Badge
                    variant={
                      status === "completed"
                        ? "success"
                        : status === "running"
                        ? "primary"
                        : status === "failed"
                        ? "destructive"
                        : "outline"
                    }
                    size="xs"
                    className="capitalize"
                  >
                    {status}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Failure Notification & Retry */}
      {isFailed && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/30 space-y-3">
          <div className="flex items-start gap-2 text-destructive text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-semibold block">Preparation Stopped</span>
              <span>{currentJob?.error || "An error occurred during schema preparation."}</span>
            </div>
          </div>
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => retryMutation.mutate()}
              isLoading={retryMutation.isPending}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Retry Preparation
            </Button>
          </div>
        </div>
      )}

      {/* Completion CTA */}
      {isSucceeded && (
        <div className="pt-2">
          <Button
            variant="primary"
            size="md"
            onClick={onComplete}
            className="w-full justify-center"
            icon={<ArrowRight className="w-4 h-4" />}
          >
            Enter Conversational BI Workspace
          </Button>
        </div>
      )}
    </div>
  );
}


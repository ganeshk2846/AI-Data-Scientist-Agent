"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchSetupStatus } from "@/lib/api";
import { GroqConnectionForm } from "./GroqConnectionForm";
import { DatabaseConnectionForm } from "./DatabaseConnectionForm";
import { PreparationProgress } from "./PreparationProgress";
import {
  Sparkles,
  Database,
  Binary,
  CheckCircle2,
  Lock,
  Layers,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface SetupReadinessGuardProps {
  children: React.ReactNode;
}

export function SetupReadinessGuard({ children }: SetupReadinessGuardProps) {
  const queryClient = useQueryClient();
  const [activeStepOverride, setActiveStepOverride] = useState<number | null>(null);

  const { data: setupData, isLoading, refetch } = useQuery({
    queryKey: ["setupStatus"],
    queryFn: fetchSetupStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.preparation_status === "RUNNING") {
        return 1500;
      }
      return 8000;
    },
  });

  const llmConnected = setupData?.llm_status === "CONNECTED";
  const dbConnected = setupData?.database_status === "CONNECTED";
  const prepCompleted = setupData?.preparation_status === "COMPLETED";
  const chatReady = setupData?.chat_ready;

  // Determine current wizard step automatically from backend state
  let currentStep = 1;
  if (!llmConnected) {
    currentStep = 1;
  } else if (!dbConnected) {
    currentStep = 2;
  } else if (!prepCompleted) {
    currentStep = 3;
  } else {
    currentStep = 4; // All complete
  }

  const effectiveStep = activeStepOverride !== null ? activeStepOverride : currentStep;

  // If chat is ready and no override, render the conversational BI workspace
  if (!isLoading && chatReady && activeStepOverride === null) {
    return <>{children}</>;
  }

  if (isLoading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="p-4 rounded-2xl bg-primary/10 text-primary border border-primary/20 animate-pulse">
          <RefreshCw className="w-8 h-8 animate-spin" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">
            Verifying System Readiness...
          </h3>
          <p className="text-xs text-muted-foreground">
            Checking Groq LLM inference channel, active database connection, and retrieval indexes.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Wizard Step Navigation Bar */}
      <div className="bg-card/75 border border-border/80 backdrop-blur-md rounded-2xl p-4 sm:p-5 shadow-sm">
        <div className="flex items-center justify-between gap-2 flex-wrap sm:flex-nowrap">
          {/* Step 1: LLM */}
          <button
            type="button"
            onClick={() => setActiveStepOverride(1)}
            className={`flex items-center gap-3 p-2 rounded-xl transition-all cursor-pointer text-left ${
              effectiveStep === 1
                ? "bg-primary/10 border border-primary/30"
                : "opacity-80 hover:opacity-100"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
                llmConnected
                  ? "bg-success text-white"
                  : effectiveStep === 1
                  ? "bg-primary text-white"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {llmConnected ? <CheckCircle2 className="w-4 h-4" /> : "1"}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-foreground">1. Groq LLM</span>
                {llmConnected && (
                  <Badge variant="success" size="xs">
                    Connected
                  </Badge>
                )}
              </div>
              <span className="text-[11px] text-muted-foreground block truncate max-w-[130px]">
                {setupData?.llm?.model || "Select Model & Key"}
              </span>
            </div>
          </button>

          <div className="hidden sm:block text-muted-foreground/40 font-mono">→</div>

          {/* Step 2: Database */}
          <button
            type="button"
            onClick={() => setActiveStepOverride(2)}
            disabled={!llmConnected}
            className={`flex items-center gap-3 p-2 rounded-xl transition-all text-left ${
              !llmConnected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
            } ${
              effectiveStep === 2
                ? "bg-primary/10 border border-primary/30"
                : "opacity-80 hover:opacity-100"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
                dbConnected
                  ? "bg-success text-white"
                  : effectiveStep === 2
                  ? "bg-primary text-white"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {dbConnected ? <CheckCircle2 className="w-4 h-4" /> : "2"}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-foreground">2. Database</span>
                {dbConnected && (
                  <Badge variant="success" size="xs">
                    Connected
                  </Badge>
                )}
              </div>
              <span className="text-[11px] text-muted-foreground block truncate max-w-[130px]">
                {setupData?.database?.name || "SQLite / Postgres / MySQL"}
              </span>
            </div>
          </button>

          <div className="hidden sm:block text-muted-foreground/40 font-mono">→</div>

          {/* Step 3: Preparation */}
          <button
            type="button"
            onClick={() => setActiveStepOverride(3)}
            disabled={!dbConnected}
            className={`flex items-center gap-3 p-2 rounded-xl transition-all text-left ${
              !dbConnected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
            } ${
              effectiveStep === 3
                ? "bg-primary/10 border border-primary/30"
                : "opacity-80 hover:opacity-100"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
                prepCompleted
                  ? "bg-success text-white"
                  : effectiveStep === 3
                  ? "bg-primary text-white"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {prepCompleted ? <CheckCircle2 className="w-4 h-4" /> : "3"}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-foreground">3. Preparation</span>
                {prepCompleted && (
                  <Badge variant="success" size="xs">
                    Ready
                  </Badge>
                )}
              </div>
              <span className="text-[11px] text-muted-foreground block truncate max-w-[130px]">
                {prepCompleted ? "7 Stages Complete" : "Vector & BM25 Indexes"}
              </span>
            </div>
          </button>
        </div>
      </div>

      {/* Wizard Content Step Panels */}
      <div>
        {effectiveStep === 1 && (
          <GroqConnectionForm
            showContinueButton={true}
            onContinue={() => {
              setActiveStepOverride(null);
              queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
            }}
            onSuccess={() => {
              setActiveStepOverride(null);
              queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
            }}
          />
        )}

        {effectiveStep === 2 && (
          <DatabaseConnectionForm
            onSuccess={() => {
              setActiveStepOverride(null);
              queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
            }}
            onNavigateToPreparation={() => {
              setActiveStepOverride(3);
              queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
            }}
          />
        )}

        {effectiveStep === 3 && (
          <PreparationProgress
            onComplete={() => {
              setActiveStepOverride(null);
              queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
            }}
          />
        )}
      </div>
    </div>
  );
}

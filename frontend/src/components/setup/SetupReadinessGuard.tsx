"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchSetupStatus } from "@/lib/api";
import { GroqConnectionForm } from "./GroqConnectionForm";
import { DatabaseConnectionForm } from "./DatabaseConnectionForm";
import { PreparationProgress } from "./PreparationProgress";
import { CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

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
    // Shaped like what loads — the thread's own header, strip and composer —
    // so nothing shifts when the real screen lands. No spinner.
    return (
      <div className="space-y-10" aria-busy="true">
        <div>
          <span className="skeleton block h-[44px] w-[22rem] max-w-full rounded-card" />
          <span className="skeleton mt-4 block h-[14px] w-[28rem] max-w-full" />
        </div>
        <div className="plane-raised grid grid-cols-2 divide-x divide-[var(--rule)] lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="px-5 py-5">
              <span className="skeleton block h-[11px] w-24" />
              <span className="skeleton mt-3 block h-[38px] w-28" />
            </div>
          ))}
        </div>
        <span className="skeleton block h-[64px] w-full rounded-card" />
        <p className="text-label text-muted" role="status">
          Checking the model, the database connection and the retrieval indexes…
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-10 py-4">
      {/* Wizard Step Navigation Bar */}
      <div className="bg-surface border border-[var(--border)] rounded-card p-4 sm:p-5">
        <div className="flex items-center justify-between gap-2 flex-wrap sm:flex-nowrap">
          {/* Step 1: LLM */}
          <button
            type="button"
            onClick={() => setActiveStepOverride(1)}
            className={`flex items-center gap-3 p-2 rounded-card transition-colors cursor-pointer text-left ${
              effectiveStep === 1
                ? "bg-raised border border-[var(--control)]"
                : "opacity-80 hover:opacity-100"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-control flex items-center justify-center font-semibold text-label shrink-0 ${
                llmConnected
                  ? "bg-pill-positive-bg text-pill-positive-ink"
                  : effectiveStep === 1
                  ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                  : "bg-raised text-muted"
              }`}
            >
              {llmConnected ? <CheckCircle2 className="w-4 h-4" /> : "1"}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-label font-semibold text-text">1. Model</span>
                {llmConnected && (
                  <Badge variant="success" size="xs">
                    Connected
                  </Badge>
                )}
              </div>
              <span className="text-micro text-muted block truncate max-w-[130px]">
                {setupData?.llm?.model || "Choose a model and key"}
              </span>
            </div>
          </button>

          <div className="hidden sm:block text-muted/40 font-mono">→</div>

          {/* Step 2: Database */}
          <button
            type="button"
            onClick={() => setActiveStepOverride(2)}
            disabled={!llmConnected}
            className={`flex items-center gap-3 p-2 rounded-card transition-colors text-left ${
              !llmConnected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
            } ${
              effectiveStep === 2
                ? "bg-raised border border-[var(--control)]"
                : "opacity-80 hover:opacity-100"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-control flex items-center justify-center font-semibold text-label shrink-0 ${
                dbConnected
                  ? "bg-pill-positive-bg text-pill-positive-ink"
                  : effectiveStep === 2
                  ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                  : "bg-raised text-muted"
              }`}
            >
              {dbConnected ? <CheckCircle2 className="w-4 h-4" /> : "2"}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-label font-semibold text-text">2. Database</span>
                {dbConnected && (
                  <Badge variant="success" size="xs">
                    Connected
                  </Badge>
                )}
              </div>
              <span className="text-micro text-muted block truncate max-w-[130px]">
                {setupData?.database?.name || "SQLite, Postgres or MySQL"}
              </span>
            </div>
          </button>

          <div className="hidden sm:block text-muted/40 font-mono">→</div>

          {/* Step 3: Preparation */}
          <button
            type="button"
            onClick={() => setActiveStepOverride(3)}
            disabled={!dbConnected}
            className={`flex items-center gap-3 p-2 rounded-card transition-colors text-left ${
              !dbConnected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
            } ${
              effectiveStep === 3
                ? "bg-raised border border-[var(--control)]"
                : "opacity-80 hover:opacity-100"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-control flex items-center justify-center font-semibold text-label shrink-0 ${
                prepCompleted
                  ? "bg-pill-positive-bg text-pill-positive-ink"
                  : effectiveStep === 3
                  ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                  : "bg-raised text-muted"
              }`}
            >
              {prepCompleted ? <CheckCircle2 className="w-4 h-4" /> : "3"}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-label font-semibold text-text">3. Preparation</span>
                {prepCompleted && (
                  <Badge variant="success" size="xs">
                    Ready
                  </Badge>
                )}
              </div>
              <span className="text-micro text-muted block truncate max-w-[130px]">
                {prepCompleted ? "All stages complete" : "Vector and keyword indexes"}
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


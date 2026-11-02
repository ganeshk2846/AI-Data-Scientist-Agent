import React from "react";
import { User, AlertCircle } from "lucide-react";
import { MultiAgentWorkflowResult } from "@/types/api";
import { StreamingStepper } from "./StreamingStepper";
import { ClarificationPrompt } from "./ClarificationPrompt";
import { RefusalBanner } from "./RefusalBanner";
import { ArtifactCard } from "./ArtifactCard";

export interface ChatTurn {
  turnId: string;
  userQuery: string;
  timestamp: string;
  result?: MultiAgentWorkflowResult;
  error?: string;
  isStreaming?: boolean;
  activeStepKey?: string;
  activeStepMessage?: string;
  completedSteps?: string[];
  activeTab?: "narrative" | "chart" | "analysis" | "sql" | "data" | "plan" | "trace";
}

export interface ChatMessageTurnProps {
  turn: ChatTurn;
  onTabChange: (tab: ChatTurn["activeTab"]) => void;
  onSelectClarification: (inferredQuery: string) => void;
  onSelectFollowUp: (qText: string) => void;
}

export function ChatMessageTurn({
  turn,
  onTabChange,
  onSelectClarification,
  onSelectFollowUp,
}: ChatMessageTurnProps) {
  const { result, isStreaming, error } = turn;

  return (
    <div className="space-y-4">
      {/* 1. User Message Bubble */}
      <div className="flex justify-end">
        <div className="max-w-2xl p-4 rounded-2xl rounded-tr-sm bg-primary text-white shadow-md space-y-1.5">
          <div className="flex items-center gap-2 text-xs opacity-90 pb-1 border-b border-white/20">
            <User className="w-3.5 h-3.5" />
            <span className="font-semibold">You</span>
            <span className="text-[10px] ml-auto font-mono opacity-80">{turn.timestamp}</span>
          </div>
          <p className="text-sm font-medium pt-0.5 leading-relaxed">{turn.userQuery}</p>
          {result?.standalone_query && result.standalone_query !== turn.userQuery && (
            <p className="text-[11px] opacity-85 italic pt-1 border-t border-white/10">
              ContextResolver Standalone Rewrite: "{result.standalone_query}"
            </p>
          )}
        </div>
      </div>

      {/* 2. Agent Streaming Live DAG Stepper */}
      {isStreaming && (
        <StreamingStepper
          activeStepKey={turn.activeStepKey}
          activeStepMessage={turn.activeStepMessage}
          completedSteps={turn.completedSteps}
        />
      )}

      {/* 3. Execution Error Message */}
      {error && (
        <div className="p-5 rounded-2xl border border-destructive/40 bg-destructive/10 text-destructive flex items-start gap-3 shadow-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-semibold text-sm">Execution Interrupted</h3>
            <p className="text-xs text-foreground/80 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* 4. Agent Completed Results & Specialized Views */}
      {result && !isStreaming && (
        <div className="space-y-4">
          {/* Clarification Alert if triggered */}
          {result.clarification?.needs_clarification && (
            <ClarificationPrompt
              clarification={result.clarification}
              onSelectOption={onSelectClarification}
            />
          )}

          {/* Answerability Refusal Alert if triggered */}
          {!result.answerability.is_answerable && (
            <RefusalBanner answerability={result.answerability} />
          )}

          {/* Full Artifact Card with Sub-tabs and Follow-ups */}
          <ArtifactCard
            result={result}
            turnId={turn.turnId}
            activeTab={turn.activeTab || "narrative"}
            onTabChange={onTabChange}
            onSelectFollowUp={onSelectFollowUp}
          />
        </div>
      )}
    </div>
  );
}


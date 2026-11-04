"use client";

import React from "react";
import { MultiAgentWorkflowResult } from "@/types/api";
import { StreamingStepper, StepView } from "./StreamingStepper";
import { AnswerView } from "./AnswerView";
import { Notice } from "@/components/ui/Notice";
import { Button } from "@/components/ui/Button";

export interface ChatTurn {
  turnId: string;
  userQuery: string;
  timestamp: string;
  result?: MultiAgentWorkflowResult;
  error?: string;
  isStreaming?: boolean;
  /** Steps observed live over SSE, in arrival order. */
  liveSteps?: StepView[];
  /** When the step currently running began, for the live counter. */
  runningSince?: number | null;
}

interface ChatMessageTurnProps {
  turn: ChatTurn;
  onAsk: (question: string) => void;
  onRetry: (question: string) => void;
}

/**
 * One exchange: the question asked, then the answer being built or the answer
 * itself.
 *
 * The question is a quiet right-aligned line rather than a filled bubble — a
 * coloured bubble on every turn would spend most of the screen's colour budget
 * on chrome that carries no information.
 */
export function ChatMessageTurn({ turn, onAsk, onRetry }: ChatMessageTurnProps) {
  const { result, isStreaming, error } = turn;

  return (
    <article className="space-y-7" aria-label={`Question: ${turn.userQuery}`}>
      <div className="flex flex-col items-end gap-1.5 border-b border-[var(--rule)] pb-6">
        <h2 className="max-w-[46rem] text-balance text-right font-display text-[clamp(1.5rem,2.4vw,2.125rem)] leading-[1.1] text-text">
          {turn.userQuery}
        </h2>
        <p className="num text-label text-faint">{turn.timestamp}</p>
      </div>

      {isStreaming ? (
        <StreamingStepper
          steps={turn.liveSteps ?? []}
          runningSince={turn.runningSince ?? null}
          live
        />
      ) : null}

      {error ? (
        <Notice
          tone="negative"
          title="The analysis did not finish"
          action={
            <Button size="sm" variant="secondary" onClick={() => onRetry(turn.userQuery)}>
              Try again
            </Button>
          }
        >
          {error}
        </Notice>
      ) : null}

      {result && !isStreaming ? <AnswerView result={result} onAsk={onAsk} /> : null}
    </article>
  );
}

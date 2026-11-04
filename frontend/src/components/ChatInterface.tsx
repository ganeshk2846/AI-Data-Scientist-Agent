"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { History, Plus } from "lucide-react";
import { executeChatQuery, streamChatQuery, fetchSessionDetail } from "@/lib/api";
import { useSession } from "@/lib/useSession";
import { ChatInput } from "./chat/ChatInput";
import { Overview } from "./Overview";
import { ChatMessageTurn, ChatTurn } from "./chat/ChatMessageTurn";
import { StepView } from "./chat/StreamingStepper";
import { SessionsDrawer } from "./chat/SessionsDrawer";
import { Button } from "./ui/Button";
import { useQuery } from "@tanstack/react-query";
import { fetchReadiness } from "@/lib/api";
import { formatFigure, databaseName } from "@/lib/format";

function newTurnId(): string {
  return `turn-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * The thread.
 *
 * Streaming is the normal path; the REST endpoint is the fallback when the
 * stream closes without delivering a result. Both end in the same validated
 * result object, so the rendering path below never has to care which ran.
 */
export function ChatInterface() {
  const { sessionId, createNewSession, switchSession } = useSession();
  const [queryInput, setQueryInput] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);


  useEffect(() => {
    // Only follow the thread down while a turn is in flight, so a reader who
    // has scrolled up to re-read an answer is not yanked back.
    if (isSubmitting) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, isSubmitting]);

  const patchTurn = useCallback((turnId: string, patch: Partial<ChatTurn>) => {
    setTurns((prev) => prev.map((t) => (t.turnId === turnId ? { ...t, ...patch } : t)));
  }, []);

  const ask = useCallback(
    async (text: string) => {
      const question = text.trim();
      if (!question || isSubmitting) return;

      const turnId = newTurnId();
      setTurns((prev) => [
        ...prev,
        {
          turnId,
          userQuery: question,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          isStreaming: true,
          liveSteps: [],
          runningSince: Date.now(),
        },
      ]);
      setIsSubmitting(true);
      setQueryInput("");

      let received = false;

      /**
       * Each progress event closes the previous step and opens a new one. The
       * backend does not send a duration on the live events, so the browser's
       * own wall-clock is recorded and clearly labelled as such; the
       * authoritative durations replace it when the result lands.
       */
      const onProgress = (step: string, message: string) => {
        const now = Date.now();
        setTurns((prev) =>
          prev.map((t) => {
            if (t.turnId !== turnId) return t;
            const previous = [...(t.liveSteps ?? [])];
            const last = previous[previous.length - 1];
            if (last && last.status === "running") {
              previous[previous.length - 1] = {
                ...last,
                status: "succeeded",
                elapsedMs: t.runningSince ? now - t.runningSince : null,
              };
            }
            const next: StepView = { step, status: "running", message, durationMs: null };
            return { ...t, liveSteps: [...previous, next], runningSince: now };
          })
        );
      };

      try {
        await streamChatQuery(
          question,
          sessionId,
          onProgress,
          (result) => {
            received = true;
            patchTurn(turnId, { result, isStreaming: false, runningSince: null });
          },
          (message) => {
            // A stream-level error is recorded but does not end the turn: the
            // REST fallback below may still produce the answer.
            console.warn("Stream reported an error:", message);
          }
        );

        if (!received) {
          const fallback = await executeChatQuery(question, sessionId);
          patchTurn(turnId, { result: fallback, isStreaming: false, runningSince: null });
        }
      } catch (streamError) {
        console.warn("Stream failed, falling back to the REST endpoint:", streamError);
        try {
          const fallback = await executeChatQuery(question, sessionId);
          patchTurn(turnId, { result: fallback, isStreaming: false, runningSince: null });
        } catch (restError) {
          patchTurn(turnId, {
            error:
              restError instanceof Error
                ? restError.message
                : "The agent could not be reached. Check that the backend is running.",
            isStreaming: false,
            runningSince: null,
          });
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [isSubmitting, patchTurn, sessionId]
  );

  const startNewSession = useCallback(() => {
    createNewSession();
    setTurns([]);
    setQueryInput("");
  }, [createNewSession]);

  const openSession = useCallback(
    async (targetId: string) => {
      switchSession(targetId);
      setTurns([]);
      setIsHistoryOpen(false);
      try {
        const detail = await fetchSessionDetail(targetId);
        const restored = (detail.turns ?? [])
          .filter((t) => t.role === "user")
          .map<ChatTurn>((t) => ({
            turnId: t.turn_id,
            userQuery: t.content,
            timestamp: new Date(t.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          }));
        setTurns(restored);
      } catch (e) {
        console.warn("Could not load this session's history:", e);
      }
    },
    [switchSession]
  );

  const isEmpty = turns.length === 0;

  return (
    // An empty thread sizes to its content: pinning the composer to the bottom
    // of the viewport would leave half a screen of nothing above it.
    <div className={isEmpty ? "flex flex-col" : "flex min-h-[calc(100vh-7rem)] flex-col"}>
      {/* On an empty thread the hero carries the screen's h1 and says this
          better than a title bar can, so only the controls are kept. Once a
          question has been asked the thread names itself. */}
      <header
        className={
          isEmpty
            ? "flex flex-wrap items-center justify-end gap-3 pb-4"
            : "flex flex-wrap items-start justify-between gap-3 pb-7"
        }
      >
        {isEmpty ? null : (
          <div className="min-w-0">
            <h1 className="font-display text-[clamp(2rem,3.4vw,2.75rem)] leading-[1.05] tracking-[-0.02em] text-text">
              Ask the data
            </h1>
            <p className="mt-2 max-w-prose-measure text-body text-muted">
              Every figure comes back with the query that produced it.
            </p>
          </div>
        )}
        <div className="flex shrink-0 items-center gap-2">
          <Button size="sm" variant="ghost" icon={<History className="h-3.5 w-3.5" />} onClick={() => setIsHistoryOpen(true)}>
            History
          </Button>
          <Button size="sm" variant="secondary" icon={<Plus className="h-3.5 w-3.5" />} onClick={startNewSession}>
            New question
          </Button>
        </div>
      </header>

      <div className={isEmpty ? "space-y-10" : "flex-1 space-y-10"}>
        {isEmpty ? (
          <Overview onAsk={ask} />
        ) : (
          turns.map((turn) => (
            <ChatMessageTurn key={turn.turnId} turn={turn} onAsk={ask} onRetry={ask} />
          ))
        )}
        <div ref={endRef} />
      </div>

      <div
        className={
          isEmpty
            ? "mt-6"
            : "sticky bottom-0 -mx-4 mt-8 bg-ground px-4 pb-4 pt-3 sm:-mx-6 sm:px-6"
        }
      >
        <ChatInput
          value={queryInput}
          onChange={setQueryInput}
          onSubmit={() => ask(queryInput)}
          isSubmitting={isSubmitting}
        />
      </div>

      <SessionsDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        activeSessionId={sessionId}
        onSelectSession={openSession}
        onNewSession={startNewSession}
      />
    </div>
  );
}

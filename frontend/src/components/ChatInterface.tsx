"use client";

import React, { useState, useEffect, useRef } from "react";
import { executeChatQuery, streamChatQuery, fetchSessionDetail } from "@/lib/api";
import { useSession } from "@/lib/useSession";
import { ChatInput } from "./chat/ChatInput";
import { ChatMessageTurn, ChatTurn } from "./chat/ChatMessageTurn";
import { SessionsDrawer } from "./chat/SessionsDrawer";
import { MessageSquare } from "lucide-react";

export function ChatInterface() {
  const { sessionId, createNewSession, switchSession } = useSession();
  const [queryInput, setQueryInput] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const turnsEndRef = useRef<HTMLDivElement>(null);

  // Smooth auto-scroll when turns update
  useEffect(() => {
    turnsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const handleNewSession = () => {
    createNewSession();
    setQueryInput("");
    setTurns([]);
  };

  const handleSelectSessionFromDrawer = async (targetId: string) => {
    switchSession(targetId);
    setTurns([]);
    try {
      const detail = await fetchSessionDetail(targetId);
      if (detail && detail.turns && detail.turns.length > 0) {
        const loadedTurns: ChatTurn[] = detail.turns.map((t) => ({
          turnId: t.turn_id,
          userQuery: t.content,
          timestamp: new Date(t.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          activeTab: "narrative",
        }));
        setTurns(loadedTurns);
      }
    } catch (e) {
      console.warn("Could not load past turns for session:", e);
    }
  };

  const executeQueryTurn = async (text: string) => {
    const qText = text.trim();
    if (!qText || isSubmitting) return;

    const turnId = "turn-" + Math.random().toString(36).substring(2, 9);
    const newTurn: ChatTurn = {
      turnId,
      userQuery: qText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      isStreaming: true,
      activeStepKey: "understanding_question",
      activeStepMessage: "Analyzing query intent and routing...",
      completedSteps: [],
      activeTab: "narrative",
    };

    setTurns((prev) => [...prev, newTurn]);
    setIsSubmitting(true);
    setQueryInput("");

    let receivedResult = false;
    try {
      await streamChatQuery(
        qText,
        sessionId,
        (stepKey, stepMessage) => {
          setTurns((prev) =>
            prev.map((t) =>
              t.turnId === turnId
                ? {
                    ...t,
                    activeStepKey: stepKey,
                    activeStepMessage: stepMessage,
                    completedSteps: Array.from(new Set([...(t.completedSteps || []), stepKey])),
                  }
                : t
            )
          );
        },
        (result) => {
          receivedResult = true;
          setTurns((prev) =>
            prev.map((t) =>
              t.turnId === turnId
                ? {
                    ...t,
                    result,
                    isStreaming: false,
                    activeTab: "narrative",
                  }
                : t
            )
          );
          setIsSubmitting(false);
        },
        async (errorMsg) => {
          console.warn("Stream error notification:", errorMsg);
        }
      );

      // Resilient fallback: If stream closed without receiving result payload, execute REST fallback
      if (!receivedResult) {
        console.warn("Stream closed without result, invoking REST fallback...");
        const fallbackResult = await executeChatQuery(qText, sessionId);
        setTurns((prev) =>
          prev.map((t) =>
            t.turnId === turnId
              ? {
                  ...t,
                  result: fallbackResult,
                  isStreaming: false,
                  activeTab: "narrative",
                }
              : t
          )
        );
      }
    } catch (err: any) {
      console.warn("Stream exception, invoking REST fallback:", err);
      try {
        const fallbackResult = await executeChatQuery(qText, sessionId);
        setTurns((prev) =>
          prev.map((t) =>
            t.turnId === turnId
              ? {
                  ...t,
                  result: fallbackResult,
                  isStreaming: false,
                  activeTab: "narrative",
                }
              : t
          )
        );
      } catch (restErr: any) {
        setTurns((prev) =>
          prev.map((t) =>
            t.turnId === turnId
              ? {
                  ...t,
                  error: restErr.message || "Query execution failed.",
                  isStreaming: false,
                }
              : t
          )
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    executeQueryTurn(queryInput);
  };

  const setTurnActiveTab = (turnId: string, tab: ChatTurn["activeTab"]) => {
    setTurns((prev) =>
      prev.map((t) => (t.turnId === turnId ? { ...t, activeTab: tab } : t))
    );
  };

  return (
    <section className="space-y-6">
      {/* 1. Main Chat Input Card */}
      <ChatInput
        queryInput={queryInput}
        onInputChange={setQueryInput}
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        onSelectSuggested={executeQueryTurn}
        sessionId={sessionId}
        onNewSession={handleNewSession}
        onOpenHistory={() => setIsHistoryOpen(true)}
      />

      {/* 2. Empty State when thread is empty */}
      {turns.length === 0 && (
        <div className="py-12 px-6 rounded-2xl border border-border/60 bg-card/40 text-center space-y-3">
          <div className="p-3 rounded-full bg-primary/10 text-primary w-fit mx-auto">
            <MessageSquare className="w-6 h-6" />
          </div>
          <h3 className="font-semibold text-base text-foreground">
            Enterprise Warehouse Intelligence Ready
          </h3>
          <p className="text-xs text-muted-foreground max-w-lg mx-auto leading-relaxed">
            Submit a business question above or select one of the Quick Inquiries.
            Queries execute through our 7-step multi-agent DAG with strict read-only AST safety.
          </p>
        </div>
      )}

      {/* 3. Conversation Thread */}
      {turns.length > 0 && (
        <div className="space-y-6">
          {turns.map((turn) => (
            <ChatMessageTurn
              key={turn.turnId}
              turn={turn}
              onTabChange={(tab) => setTurnActiveTab(turn.turnId, tab)}
              onSelectClarification={executeQueryTurn}
              onSelectFollowUp={executeQueryTurn}
            />
          ))}
          <div ref={turnsEndRef} />
        </div>
      )}

      {/* 4. Slide-Over Sessions Memory Drawer */}
      <SessionsDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        activeSessionId={sessionId}
        onSelectSession={handleSelectSessionFromDrawer}
        onNewSession={handleNewSession}
      />
    </section>
  );
}

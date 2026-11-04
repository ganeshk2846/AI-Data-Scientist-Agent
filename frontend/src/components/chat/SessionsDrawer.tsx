"use client";

import React, { useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Plus, Trash2 } from "lucide-react";
import { clsx } from "clsx";
import { fetchSessions, clearSessionApi } from "@/lib/api";
import { Button } from "../ui/Button";

interface SessionsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
}

/**
 * Past threads, in a drawer.
 *
 * It enters and leaves along the same edge, which is what makes the dismiss
 * feel obvious. Focus moves into the drawer on open and Escape closes it, so
 * it is operable without a pointer.
 */
export function SessionsDrawer({
  isOpen,
  onClose,
  activeSessionId,
  onSelectSession,
  onNewSession,
}: SessionsDrawerProps) {
  const queryClient = useQueryClient();
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["conversationSessions"],
    queryFn: fetchSessions,
    enabled: isOpen,
  });

  const clearSession = useMutation({
    mutationFn: (id: string) => clearSessionApi(id),
    onSuccess: (_result, id) => {
      queryClient.invalidateQueries({ queryKey: ["conversationSessions"] });
      if (id === activeSessionId) onNewSession();
    },
  });

  useEffect(() => {
    if (!isOpen) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Close history"
        onClick={onClose}
        className="absolute inset-0 bg-[var(--text)] opacity-20"
      />

      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Earlier questions"
        className={clsx(
          "absolute inset-y-0 right-0 flex w-full max-w-md flex-col border-l border-[var(--border)] bg-surface",
          "transition-transform duration-[240ms] ease-drawer motion-reduce:transition-none"
        )}
      >
        <header className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-4 py-3">
          <h2 className="text-section font-semibold text-text">Earlier questions</h2>
          <div className="flex items-center gap-1.5">
            <Button size="sm" variant="secondary" icon={<Plus className="h-3.5 w-3.5" />} onClick={onNewSession}>
              New
            </Button>
            <button
              ref={closeRef}
              type="button"
              onClick={onClose}
              aria-label="Close history"
              className="flex h-8 w-8 items-center justify-center rounded-control text-muted transition-colors duration-[120ms] hover:[@media(hover:hover)and(pointer:fine)]:bg-raised hover:[@media(hover:hover)and(pointer:fine)]:text-text"
            >
              <X aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        </header>

        <div className="scroll-quiet flex-1 overflow-y-auto p-3">
          {isLoading ? (
            <ul className="space-y-2" aria-label="Loading threads">
              {[0, 1, 2, 3].map((i) => (
                <li key={i} className="rounded-card border border-[var(--border)] p-3">
                  <span className="skeleton block h-[14px] w-2/3" />
                  <span className="skeleton mt-2 block h-[12px] w-1/3" />
                </li>
              ))}
            </ul>
          ) : !sessions || sessions.length === 0 ? (
            <p className="rounded-card border border-dashed border-[var(--border)] px-3 py-8 text-center text-body text-muted">
              No earlier questions yet. Ask one and it will be saved here.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {sessions.map((session) => {
                const active = session.session_id === activeSessionId;
                return (
                  <li key={session.session_id}>
                    <div
                      className={clsx(
                        "flex items-center gap-2 rounded-card border px-3 py-2.5",
                        active ? "border-[var(--control)] bg-active" : "border-[var(--border)]"
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => onSelectSession(session.session_id)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <span className="block truncate text-body text-text">
                          {session.title || "Untitled question"}
                        </span>
                        <span className="num mt-0.5 block text-label text-muted">
                          {new Date(session.updated_at).toLocaleString()}
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => clearSession.mutate(session.session_id)}
                        disabled={clearSession.isPending}
                        aria-label={`Clear ${session.title || "this question"}`}
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-muted transition-colors duration-[120ms] hover:[@media(hover:hover)and(pointer:fine)]:bg-raised hover:[@media(hover:hover)and(pointer:fine)]:text-negative disabled:opacity-40"
                      >
                        <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}

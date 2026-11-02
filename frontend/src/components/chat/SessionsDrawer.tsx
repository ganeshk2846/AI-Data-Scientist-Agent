import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchSessions, fetchSessionDetail, clearSessionApi } from "@/lib/api";
import { SessionModel } from "@/types/api";
import {
  History,
  MessageSquare,
  Plus,
  Trash2,
  X,
  Clock,
  ArrowRight,
  Database,
  RefreshCw,
} from "lucide-react";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";

export interface SessionsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
}

export function SessionsDrawer({
  isOpen,
  onClose,
  activeSessionId,
  onSelectSession,
  onNewSession,
}: SessionsDrawerProps) {
  const queryClient = useQueryClient();
  const [clearingId, setClearingId] = useState<string | null>(null);

  const { data: sessions, isLoading, refetch } = useQuery({
    queryKey: ["conversationSessions"],
    queryFn: fetchSessions,
    enabled: isOpen,
  });

  const clearMutation = useMutation({
    mutationFn: (sessId: string) => clearSessionApi(sessId),
    onSuccess: (_, sessId) => {
      queryClient.invalidateQueries({ queryKey: ["conversationSessions"] });
      if (sessId === activeSessionId) {
        onNewSession();
      }
      setClearingId(null);
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <aside className="relative w-full max-w-md h-full bg-card border-l border-border shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-muted/20">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-primary" />
            <h3 className="font-semibold text-sm text-foreground">Conversation Memory</h3>
            <Badge variant="mono" size="xs">
              agent_app.sqlite
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="xs"
              onClick={() => {
                onNewSession();
                onClose();
              }}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              New Thread
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose} title="Close drawer">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {isLoading && (
            <div className="py-12 flex flex-col items-center justify-center space-y-3 text-muted-foreground text-xs">
              <RefreshCw className="w-5 h-5 animate-spin text-primary" />
              <span>Loading saved sessions from SQLite...</span>
            </div>
          )}

          {!isLoading && (!sessions || sessions.length === 0) && (
            <div className="py-12 text-center text-xs text-muted-foreground border border-border/50 rounded-xl bg-background/40 p-6 space-y-2">
              <MessageSquare className="w-8 h-8 text-muted-foreground/40 mx-auto" />
              <p className="font-medium text-foreground/80">No prior sessions recorded</p>
              <p className="text-[11px]">
                Ask questions in the Conversational BI workspace to persist sessions in agent_app.sqlite.
              </p>
            </div>
          )}

          {!isLoading &&
            sessions &&
            sessions.map((sess: SessionModel) => {
              const isActive = sess.session_id === activeSessionId;
              const isDeleting = clearingId === sess.session_id;

              return (
                <div
                  key={sess.session_id}
                  className={`p-3.5 rounded-xl border transition-all text-xs flex flex-col gap-2 ${
                    isActive
                      ? "border-primary bg-primary/10 shadow-sm ring-1 ring-primary/30"
                      : "border-border/80 bg-background/50 hover:bg-muted/40 hover:border-border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        onSelectSession(sess.session_id);
                        onClose();
                      }}
                      className="text-left flex-1 font-medium text-foreground hover:text-primary transition-colors cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <span className="truncate max-w-[220px]">
                          {sess.title || sess.session_id}
                        </span>
                        {isActive && (
                          <Badge variant="primary" size="xs">
                            Active
                          </Badge>
                        )}
                      </div>
                    </button>

                    <Button
                      variant="ghost"
                      size="icon"
                      isLoading={isDeleting}
                      onClick={() => {
                        setClearingId(sess.session_id);
                        clearMutation.mutate(sess.session_id);
                      }}
                      title="Clear session history"
                      className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground font-mono pt-1 border-t border-border/40">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(sess.updated_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span className="truncate max-w-[120px] opacity-75">{sess.session_id}</span>
                  </div>
                </div>
              );
            })}
        </div>

        {/* Footer */}
        <div className="p-3.5 border-t border-border bg-muted/20 text-[11px] text-muted-foreground text-center">
          Sessions and multi-turn frames isolated in <code className="font-mono text-foreground">agent_app.sqlite</code>
        </div>
      </aside>
    </div>
  );
}


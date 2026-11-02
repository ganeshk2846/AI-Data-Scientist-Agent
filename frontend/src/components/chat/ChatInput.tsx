import React from "react";
import {
  History,
  Lightbulb,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";

export const SUGGESTED_QUERIES = [
  { text: "Show orders by status and their total amount", category: "Orders" },
  { text: "What are our total sales and order counts by year?", category: "Trend" },
  { text: "What are the top 5 product categories by revenue?", category: "Catalog" },
  { text: "How many customers belong to each customer segment?", category: "Segments" },
  { text: "What is the churn risk and revenue at risk across customer segments?", category: "Churn" },
  { text: "compare revenue", category: "Clarify" },
  { text: "What is the current bitcoin price?", category: "Refusal" },
] as const;

export interface ChatInputProps {
  queryInput: string;
  onInputChange: (val: string) => void;
  onSubmit: (e?: React.FormEvent) => void;
  isSubmitting: boolean;
  onSelectSuggested: (text: string) => void;
  sessionId: string;
  onNewSession: () => void;
  onOpenHistory: () => void;
}

export function ChatInput({
  queryInput,
  onInputChange,
  onSubmit,
  isSubmitting,
  onSelectSuggested,
  sessionId,
  onNewSession,
  onOpenHistory,
}: ChatInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (queryInput.trim() && !isSubmitting) {
        onSubmit();
      }
    }
  };

  return (
    <div className="p-6 rounded-2xl border border-border/80 bg-card/90 shadow-lg space-y-4">
      {/* Top Bar with Session Indicators & History Drawer Toggle */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-primary/15 text-primary">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-foreground">
                Conversational BI Assistant
              </h2>
              <Badge variant="primary" size="xs">
                Real-Time SSE DAG
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Ask natural language business questions with schema grounding & AST SQL safety
            </p>
          </div>
        </div>

        {/* Session Controls */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <Badge
            variant="mono"
            size="xs"
            className="text-[11px] px-2.5 py-1 text-muted-foreground bg-muted/60"
            title="Active Session ID isolated in agent_app.sqlite"
          >
            {sessionId}
          </Badge>

          <Button
            type="button"
            variant="outline"
            size="xs"
            onClick={onOpenHistory}
            icon={<History className="w-3.5 h-3.5" />}
            title="View saved session threads"
          >
            History
          </Button>

          <Button
            type="button"
            variant="outline"
            size="xs"
            onClick={onNewSession}
            icon={<Plus className="w-3.5 h-3.5" />}
            title="Start new isolated conversation thread"
          >
            New
          </Button>
        </div>
      </div>

      {/* Input Form with Send Button */}
      <form onSubmit={onSubmit} className="relative">
        <input
          type="text"
          placeholder="Ask any warehouse question (e.g. 'Show orders by status and total revenue')..."
          value={queryInput}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSubmitting}
          className="w-full pl-4 pr-32 py-3.5 text-sm bg-background/80 border border-border/80 rounded-xl text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/40 disabled:opacity-50 transition-all shadow-inner"
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={!queryInput.trim() || isSubmitting}
          isLoading={isSubmitting}
          icon={!isSubmitting ? <Send className="w-3.5 h-3.5" /> : undefined}
          className="absolute right-2 top-2 px-4 py-2"
        >
          {isSubmitting ? "Running DAG..." : "Ask Agent"}
        </Button>
      </form>

      {/* Starter Suggested Queries Rack */}
      <div className="flex items-center gap-1.5 text-xs flex-wrap pt-1">
        <span className="text-muted-foreground flex items-center gap-1 font-medium pr-1">
          <Lightbulb className="w-3.5 h-3.5 text-warning" />
          <span>Quick Inquiries:</span>
        </span>
        {SUGGESTED_QUERIES.map((sq, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSelectSuggested(sq.text)}
            disabled={isSubmitting}
            className="px-2.5 py-1 rounded-lg bg-background/60 border border-border/70 hover:border-primary/60 hover:bg-muted/40 text-foreground/80 hover:text-foreground text-[11px] transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1 shadow-sm"
          >
            <span className="text-[10px] text-muted-foreground font-mono">[{sq.category}]</span>
            <span>{sq.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}


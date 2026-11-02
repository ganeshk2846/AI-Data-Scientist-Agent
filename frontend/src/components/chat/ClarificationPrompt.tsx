import React from "react";
import { ArrowRight, HelpCircle } from "lucide-react";
import { ClarificationResponse } from "@/types/api";

export interface ClarificationPromptProps {
  clarification: ClarificationResponse;
  onSelectOption: (inferredQuery: string) => void;
  disabled?: boolean;
}

export function ClarificationPrompt({
  clarification,
  onSelectOption,
  disabled = false,
}: ClarificationPromptProps) {
  if (!clarification.needs_clarification) return null;

  return (
    <div className="p-5 rounded-xl border border-primary/40 bg-primary/10 shadow-sm space-y-4">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-primary/20 text-primary flex-shrink-0 mt-0.5">
          <HelpCircle className="w-5 h-5" />
        </div>
        <div className="flex-1 space-y-1">
          <h3 className="font-semibold text-sm text-foreground">
            {clarification.question || "Clarification Required"}
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {clarification.ambiguity_reason || "The inquiry has multiple valid interpretations across the warehouse."}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
        {clarification.options.map((opt) => (
          <button
            key={opt.option_id}
            type="button"
            disabled={disabled}
            onClick={() => onSelectOption(opt.inferred_query)}
            className="p-3.5 rounded-xl border border-border/80 bg-card hover:border-primary/70 hover:bg-muted/40 text-left text-xs space-y-1.5 transition-all group shadow-sm disabled:opacity-50 cursor-pointer"
          >
            <div className="flex items-center justify-between font-semibold text-foreground group-hover:text-primary transition-colors">
              <span>{opt.label}</span>
              <ArrowRight className="w-3.5 h-3.5 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-primary" />
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">{opt.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}


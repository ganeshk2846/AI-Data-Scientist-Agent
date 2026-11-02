import React from "react";
import { ShieldAlert, Database } from "lucide-react";
import { z } from "zod";
import { AnswerabilityAssessmentSchema } from "@/types/api";

export type AnswerabilityAssessment = z.infer<typeof AnswerabilityAssessmentSchema>;

export interface RefusalBannerProps {
  answerability: AnswerabilityAssessment;
}

export function RefusalBanner({ answerability }: RefusalBannerProps) {
  if (answerability.is_answerable) return null;

  const alternatives: string[] = answerability.available_alternatives || [];

  return (
    <div className="p-5 rounded-xl border border-warning/40 bg-warning/10 shadow-sm space-y-3.5">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-warning/20 text-warning flex-shrink-0 mt-0.5">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-sm text-warning">
              Honest Refusal: Question Outside Warehouse Scope
            </h3>
            {answerability.abstention_type && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-warning/20 text-warning border border-warning/30 uppercase">
                {answerability.abstention_type}
              </span>
            )}
          </div>
          <p className="text-xs text-foreground/85 leading-relaxed">
            {answerability.refusal_reason ||
              "The requested data or metric falls outside the verified e-commerce warehouse boundary."}
          </p>
        </div>
      </div>

      {alternatives.length > 0 && (
        <div className="pt-3 border-t border-warning/20 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground/90">
            <Database className="w-3.5 h-3.5 text-warning" />
            <span>Supported Warehouse Domains You Can Query:</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {alternatives.map((alt: string, i: number) => (
              <span
                key={i}
                className="text-[11px] px-2.5 py-1 rounded-lg bg-background/60 border border-warning/30 text-foreground/80 font-medium"
              >
                {alt}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

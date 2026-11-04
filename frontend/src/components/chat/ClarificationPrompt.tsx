"use client";

import React from "react";
import { ClarificationResponse } from "@/types/api";

interface ClarificationPromptProps {
  clarification: ClarificationResponse;
  onSelectOption: (inferredQuery: string) => void;
}

/**
 * The agent asking rather than guessing. Styled as a question, not an error —
 * declining to guess is the product working correctly.
 */
export function ClarificationPrompt({ clarification, onSelectOption }: ClarificationPromptProps) {
  const { question, ambiguity_reason, options, default_interpretation } = clarification;

  return (
    <section
      aria-label="Clarification needed"
      className="space-y-3 rounded-card border border-[var(--border)] bg-surface p-4"
    >
      <div className="space-y-1">
        <h3 className="text-headline font-semibold text-text">
          {question ?? "Which of these did you mean?"}
        </h3>
        {ambiguity_reason ? <p className="text-body text-muted">{ambiguity_reason}</p> : null}
      </div>

      {options.length > 0 ? (
        <ul className="space-y-1.5">
          {options.map((option) => (
            <li key={option.option_id}>
              <button
                type="button"
                onClick={() => onSelectOption(option.inferred_query)}
                className={[
                  "w-full rounded-card border border-[var(--border)] px-3.5 py-2.5 text-left",
                  "transition-[background-color,transform] duration-[140ms] ease-out",
                  "hover:[@media(hover:hover)and(pointer:fine)]:bg-raised",
                  "active:scale-[0.99] motion-reduce:active:scale-100",
                ].join(" ")}
              >
                <span className="block text-body font-medium text-text">{option.label}</span>
                {option.description ? (
                  <span className="mt-0.5 block text-label text-muted">{option.description}</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {default_interpretation ? (
        <p className="border-t border-[var(--rule)] pt-3 text-label text-muted">
          If you ask again without choosing, it will read your question as:{" "}
          <span className="text-text">{default_interpretation}</span>
        </p>
      ) : null}
    </section>
  );
}

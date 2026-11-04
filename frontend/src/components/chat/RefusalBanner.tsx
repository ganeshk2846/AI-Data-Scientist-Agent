"use client";

import React from "react";
import { AnswerabilityAssessment } from "@/types/api";

interface RefusalBannerProps {
  answerability: AnswerabilityAssessment;
  /** Sends one of the alternatives as a new question. */
  onSelectAlternative?: (question: string) => void;
}

/**
 * The agent declining to answer what the data cannot support.
 *
 * Presented as a finding with a way forward, not as an error: abstaining rather
 * than inventing a number is the behaviour this product is built around, so it
 * is not coloured red and does not carry an alert icon.
 */
export function RefusalBanner({ answerability, onSelectAlternative }: RefusalBannerProps) {
  const { refusal_reason, available_alternatives, abstention_type } = answerability;

  return (
    <section
      aria-label="Question not answerable from this data"
      className="space-y-3 rounded-card border border-[var(--border)] bg-surface p-4"
    >
      <div className="space-y-1">
        <h3 className="text-headline font-semibold text-text">
          This can&rsquo;t be answered from the connected data
        </h3>
        <p className="text-body text-text">
          {refusal_reason ??
            "The question could not be grounded in the tables available, so no figure was produced."}
        </p>
        {abstention_type ? (
          <p className="text-label text-muted">Reason recorded by the agent: {abstention_type}</p>
        ) : null}
      </div>

      {available_alternatives.length > 0 ? (
        <div className="space-y-1.5 border-t border-[var(--rule)] pt-3">
          <p className="text-label text-muted">You could ask instead:</p>
          <ul className="space-y-1.5">
            {available_alternatives.map((alternative) => (
              <li key={alternative}>
                {onSelectAlternative ? (
                  <button
                    type="button"
                    onClick={() => onSelectAlternative(alternative)}
                    className={[
                      "w-full rounded-card border border-[var(--border)] px-3.5 py-2 text-left text-body text-text",
                      "transition-[background-color,transform] duration-[140ms] ease-out",
                      "hover:[@media(hover:hover)and(pointer:fine)]:bg-raised",
                      "active:scale-[0.99] motion-reduce:active:scale-100",
                    ].join(" ")}
                  >
                    {alternative}
                  </button>
                ) : (
                  <p className="text-body text-text">{alternative}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

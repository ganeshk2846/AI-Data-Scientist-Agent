"use client";

import { MultiAgentWorkflowResult, MultiAgentWorkflowResultSchema } from "@/types/api";

const KEY = "aibi-opening-answer";
const TTL_MS = 30 * 60 * 1000;

interface Stored {
  question: string;
  savedAt: number;
  result: unknown;
}

/**
 * The opening answer, kept across page loads.
 *
 * The landing view answers a real question against the warehouse, which costs
 * one model call. React Query's cache lives in memory, so every reload spent
 * another one — enough of them in a row and the provider rate-limits the
 * account, which is exactly the wrong moment for a demo to lose its opening.
 *
 * The answer is held for thirty minutes and re-validated through the same
 * schema the network path uses, so a stored payload from an older contract is
 * discarded rather than rendered.
 */
export function readOpeningAnswer(question: string): { result: MultiAgentWorkflowResult; savedAt: number } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as Stored;
    if (stored.question !== question) return null;
    if (Date.now() - stored.savedAt > TTL_MS) return null;
    const parsed = MultiAgentWorkflowResultSchema.safeParse(stored.result);
    if (!parsed.success) return null;
    return { result: parsed.data, savedAt: stored.savedAt };
  } catch {
    return null;
  }
}

export function writeOpeningAnswer(question: string, result: MultiAgentWorkflowResult): void {
  if (typeof window === "undefined") return;
  try {
    const stored: Stored = { question, savedAt: Date.now(), result };
    window.localStorage.setItem(KEY, JSON.stringify(stored));
  } catch {
    /* storage full or blocked — the answer simply is not kept */
  }
}

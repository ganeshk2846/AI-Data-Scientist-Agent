"use client";

import React, { useEffect, useRef, useState } from "react";
import { ArrowUp } from "lucide-react";
import { clsx } from "clsx";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  /** Disables the control and says why. */
  disabledReason?: string | null;
}

/**
 * The question field.
 *
 * Enter sends and Shift+Enter makes a new line, which is the convention for a
 * thread. The textarea grows with its content to a cap, so a long question is
 * readable while being typed without the control taking over the screen.
 *
 * No animation on send: it is keyboard-initiated and repeated all session.
 */
export function ChatInput({ value, onChange, onSubmit, isSubmitting, disabledReason }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  // The question box is where the work starts, so it takes focus on load and
  // Cmd/Ctrl+K brings it back from anywhere.
  useEffect(() => {
    // Only on a device with a keyboard: autofocusing on a phone scrolls the
    // page and throws up the on-screen keyboard before anyone asked for it.
    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
      // preventScroll: focusing must not scroll the landing view past its hero.
      ref.current?.focus({ preventScroll: true });
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        ref.current?.focus({ preventScroll: true });
        ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);

  const blocked = Boolean(disabledReason);
  const [modKey, setModKey] = useState("Ctrl ");
  useEffect(() => {
    if (typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform)) setModKey("⌘");
  }, []);
  const canSend = value.trim().length > 0 && !isSubmitting && !blocked;

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) onSubmit();
    }
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSend) onSubmit();
      }}
      className="space-y-1.5"
    >
      <div
        className={clsx(
          "flex items-end gap-3 rounded-card border bg-surface px-4 py-3.5",
          "border-[var(--control)] shadow-raised focus-within:border-accent focus-within:shadow-lift",
          "transition-[border-color,box-shadow] duration-[110ms] ease-out"
        )}
      >
        <label htmlFor="question" className="sr-only">
          Ask a question about the connected data
        </label>
        <textarea
          id="question"
          ref={ref}
          rows={1}
          value={value}
          disabled={blocked}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about the connected data"
          aria-describedby={blocked ? "question-blocked" : undefined}
          className={clsx(
            "scroll-quiet min-h-[26px] flex-1 resize-none bg-transparent text-[15px] leading-relaxed text-text",
            "placeholder:text-faint focus:outline-none disabled:cursor-not-allowed"
          )}
        />
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send question"
          className={clsx(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-control",
            "bg-[var(--primary)] text-[var(--primary-ink)] shadow-raised",
            "transition-[opacity,transform,box-shadow] duration-[110ms] ease-out",
            "enabled:hover:[@media(hover:hover)and(pointer:fine)]:shadow-lift",
            "disabled:opacity-30 enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100"
          )}
        >
          <ArrowUp aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>

      {blocked ? (
        <p id="question-blocked" className="text-label text-muted">
          {disabledReason}
        </p>
      ) : (
        <p className="text-label text-faint">
          Enter to send · Shift + Enter for a new line ·{" "}
          <kbd className="num rounded-chip border border-[var(--border)] bg-raised px-1 py-0.5 text-micro text-muted">
            {modKey}K
          </kbd>{" "}
          to jump back here
        </p>
      )}
    </form>
  );
}

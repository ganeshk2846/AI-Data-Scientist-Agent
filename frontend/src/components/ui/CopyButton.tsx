"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";
import { clsx } from "clsx";

interface CopyButtonProps {
  value: string;
  /** Names the thing being copied, for the accessible label. */
  label: string;
  className?: string;
}

/**
 * Copy-to-clipboard with a confirmation that is announced, not just drawn.
 *
 * The timer is cleared on unmount so a copy inside a panel the user closes does
 * not set state on a gone component.
 */
export function CopyButton({ value, label, className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked by permissions policy; stay silent rather than
      // claiming a copy that did not happen.
      setCopied(false);
    }
  }, [value]);

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={copied ? `${label} copied` : `Copy ${label}`}
      className={clsx(
        "inline-flex h-7 items-center gap-1.5 rounded-control px-2 text-label",
        "text-muted hover:[@media(hover:hover)and(pointer:fine)]:bg-raised hover:[@media(hover:hover)and(pointer:fine)]:text-text",
        "transition-[background-color,color,transform] duration-[140ms] ease-out active:scale-[0.97] motion-reduce:active:scale-100",
        className
      )}
    >
      {copied ? (
        <Check aria-hidden="true" className="h-3.5 w-3.5 text-positive" />
      ) : (
        <Copy aria-hidden="true" className="h-3.5 w-3.5" />
      )}
      <span>{copied ? "Copied" : "Copy"}</span>
      <span role="status" aria-live="polite" className="sr-only">
        {copied ? `${label} copied to clipboard` : ""}
      </span>
    </button>
  );
}

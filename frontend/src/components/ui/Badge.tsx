import React from "react";
import { cn } from "@/lib/cn";

/**
 * A status pill: a pale tint with dark ink of the same hue, never a saturated
 * fill with white text. 11px floor, 20px tall, inside rows and beside values
 * only — never above a heading.
 *
 * The legacy variant names are kept as aliases so existing call sites keep
 * compiling while taking the new look.
 */
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "neutral"
    | "positive"
    | "negative"
    | "warning"
    | "outline"
    | "mono"
    // aliases
    | "default"
    | "primary"
    | "success"
    | "destructive";
  size?: "xs" | "sm";
}

const VARIANTS: Record<string, string> = {
  neutral: "bg-pill-neutral-bg text-pill-neutral-ink",
  positive: "bg-pill-positive-bg text-pill-positive-ink",
  negative: "bg-pill-negative-bg text-pill-negative-ink",
  warning: "bg-pill-warning-bg text-pill-warning-ink",
  outline: "bg-transparent text-muted border border-[var(--border)]",
  mono: "bg-pill-neutral-bg text-pill-neutral-ink font-mono",
  // aliases
  default: "bg-pill-neutral-bg text-pill-neutral-ink",
  primary: "bg-pill-neutral-bg text-pill-neutral-ink",
  success: "bg-pill-positive-bg text-pill-positive-ink",
  destructive: "bg-pill-negative-bg text-pill-negative-ink",
};

export function Badge({ className, variant = "neutral", size = "sm", children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-chip font-medium whitespace-nowrap",
        "h-5 px-2",
        size === "xs" ? "text-micro" : "text-label",
        VARIANTS[variant] ?? VARIANTS.neutral,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export { Badge as StatusPill };

import React from "react";
import { AlertTriangle, Info, CircleCheck, CircleAlert } from "lucide-react";
import { clsx } from "clsx";

export type NoticeTone = "neutral" | "warning" | "negative" | "positive";

interface NoticeProps {
  tone?: NoticeTone;
  title?: React.ReactNode;
  children?: React.ReactNode;
  /** A retry or follow-up control, shown at the end of the notice. */
  action?: React.ReactNode;
  className?: string;
}

const ICONS: Record<NoticeTone, typeof Info> = {
  neutral: Info,
  warning: AlertTriangle,
  negative: CircleAlert,
  positive: CircleCheck,
};

const TONES: Record<NoticeTone, string> = {
  neutral: "border-[var(--border)] bg-surface text-text",
  warning: "border-[var(--border)] bg-pill-warning-bg text-pill-warning-ink",
  negative: "border-[var(--border)] bg-pill-negative-bg text-pill-negative-ink",
  positive: "border-[var(--border)] bg-pill-positive-bg text-pill-positive-ink",
};

/**
 * A notice lives inside the block it concerns, never as a full-screen banner.
 * A notice tint is never used as a page ground.
 */
export function Notice({ tone = "neutral", title, children, action, className }: NoticeProps) {
  const Icon = ICONS[tone];
  return (
    <div
      className={clsx("flex gap-2.5 rounded-card border px-3 py-2.5", TONES[tone], className)}
      role={tone === "negative" ? "alert" : undefined}
    >
      <Icon aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 flex-1 space-y-1">
        {title ? <p className="text-body font-medium">{title}</p> : null}
        {children ? <div className="text-body leading-relaxed">{children}</div> : null}
        {action ? <div className="pt-1">{action}</div> : null}
      </div>
    </div>
  );
}

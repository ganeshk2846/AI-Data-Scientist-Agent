import React from "react";
import { cn } from "@/lib/cn";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * `primary` is near-black (inverted white on dark) — never the data hue.
   * One primary per screen.
   */
  variant?: "primary" | "secondary" | "ghost" | "danger" | "outline" | "subtle" | "destructive";
  size?: "sm" | "md" | "icon" | "xs";
  icon?: React.ReactNode;
  /** Swaps the icon for a spinner and disables the control. */
  isLoading?: boolean;
}

const VARIANTS: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-[var(--primary)] text-[var(--primary-ink)] shadow-raised hover:-translate-y-px hover:shadow-lift",
  secondary:
    "bg-surface text-text border border-[var(--control)] shadow-raised hover:border-[var(--accent-edge)] hover:-translate-y-px hover:shadow-lift",
  ghost: "bg-transparent text-muted hover:text-accent hover:bg-raised",
  danger: "bg-transparent text-negative border border-[var(--control)] hover:bg-raised",
  // aliases kept so existing call sites take the new look without churn
  outline:
    "bg-surface text-text border border-[var(--control)] shadow-raised hover:border-[var(--accent-edge)] hover:-translate-y-px hover:shadow-lift",
  subtle: "bg-transparent text-muted hover:text-accent hover:bg-raised",
  destructive: "bg-transparent text-negative border border-[var(--control)] hover:bg-raised",
};

const SIZES: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "h-9 px-3.5 text-label gap-1.5 rounded-control",
  md: "h-10 px-4 text-body gap-2 rounded-control",
  icon: "h-10 w-10 justify-center rounded-control",
  xs: "h-7 px-2.5 text-label gap-1 rounded-control",
};

/**
 * Nothing is inert under the cursor: the surface lifts a pixel, its edge warms
 * to gold and the light under it deepens, all inside 110ms. The press is
 * `scale(0.97)` — transform only, so feedback never triggers layout. Hover is
 * gated to real pointers, because touch fires a false hover on tap.
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "secondary", size = "md", icon, isLoading = false, disabled, children, type = "button", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={cn(
        "inline-flex items-center font-medium select-none",
        "transition-[transform,background-color,border-color,box-shadow,color] duration-[110ms] ease-out",
        "[@media(hover:none)]:hover:translate-y-0",
        "active:scale-[0.97]",
        "disabled:opacity-45 disabled:pointer-events-none",
        "motion-reduce:active:scale-100",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    >
      {isLoading ? (
        <Loader2 aria-hidden="true" className="h-3.5 w-3.5 shrink-0 animate-spin motion-reduce:animate-none" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children}
    </button>
  );
});

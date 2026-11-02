import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "primary" | "success" | "warning" | "destructive" | "outline" | "mono";
  size?: "xs" | "sm";
}

export function Badge({
  className,
  variant = "default",
  size = "xs",
  children,
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-muted text-muted-foreground border-border/60",
    primary: "bg-primary/15 text-primary border-primary/30",
    success: "bg-success/15 text-success border-success/30",
    warning: "bg-warning/15 text-warning border-warning/30",
    destructive: "bg-destructive/15 text-destructive border-destructive/30",
    outline: "bg-transparent text-foreground/80 border-border hover:border-border/80",
    mono: "bg-muted/80 text-foreground/90 font-mono border-border/80",
  };

  const sizeStyles = {
    xs: "text-[10px] px-1.5 py-0.5",
    sm: "text-xs px-2 py-0.5",
  };

  return (
    <span
      className={twMerge(
        clsx(
          "inline-flex items-center gap-1 font-medium rounded-full border transition-colors select-none",
          variantStyles[variant],
          sizeStyles[size],
          className
        )
      )}
      {...props}
    >
      {children}
    </span>
  );
}


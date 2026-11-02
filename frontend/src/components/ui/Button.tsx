import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { RefreshCw } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "destructive" | "subtle";
  size?: "xs" | "sm" | "md" | "icon";
  isLoading?: boolean;
  icon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "sm",
      isLoading = false,
      icon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const variantStyles = {
      primary:
        "bg-primary text-white hover:bg-primary/90 shadow-sm border border-primary/40 active:translate-y-px",
      secondary:
        "bg-muted text-foreground hover:bg-muted/80 border border-border active:translate-y-px",
      outline:
        "bg-transparent text-foreground/90 hover:text-foreground hover:bg-muted/60 border border-border hover:border-primary/40 active:translate-y-px",
      ghost:
        "bg-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-transparent active:translate-y-px",
      destructive:
        "bg-destructive/15 text-destructive hover:bg-destructive/25 border border-destructive/30 active:translate-y-px",
      subtle:
        "bg-background/80 text-foreground/80 hover:text-foreground border border-border hover:border-primary/40 active:translate-y-px",
    };

    const sizeStyles = {
      xs: "text-[11px] px-2 py-1 rounded-md gap-1",
      sm: "text-xs px-3 py-1.5 rounded-lg gap-1.5",
      md: "text-sm px-4 py-2 rounded-lg gap-2",
      icon: "p-1.5 rounded-lg",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={twMerge(
          clsx(
            "inline-flex items-center justify-center font-medium transition-all duration-150 outline-none select-none disabled:opacity-50 disabled:pointer-events-none cursor-pointer",
            variantStyles[variant],
            sizeStyles[size],
            className
          )
        )}
        {...props}
      >
        {isLoading ? (
          <RefreshCw className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
        ) : icon ? (
          <span className="flex-shrink-0">{icon}</span>
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";


"use client";

import React, { useId, useState } from "react";
import { ChevronRight } from "lucide-react";
import { clsx } from "clsx";

interface DisclosureProps {
  /** The always-visible summary line. */
  label: React.ReactNode;
  /** Right-aligned meta on the trigger line, e.g. a count. */
  meta?: React.ReactNode;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
  className?: string;
}

/**
 * An accessible expand/collapse.
 *
 * The height transition uses `grid-template-rows: 0fr -> 1fr`, which is the one
 * honest way to animate a disclosure open — there is no transform equivalent
 * for revealing content of unknown height, and animating `height` to a measured
 * pixel value breaks when the content reflows. The content stays in the DOM so
 * it remains findable by in-page search.
 */
export function Disclosure({
  label,
  meta,
  defaultOpen = false,
  open: controlledOpen,
  onOpenChange,
  children,
  className,
}: DisclosureProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;
  const panelId = useId();
  const triggerId = useId();

  function toggle() {
    const next = !open;
    if (!isControlled) setUncontrolledOpen(next);
    onOpenChange?.(next);
  }

  return (
    <div className={className}>
      <button
        type="button"
        id={triggerId}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={toggle}
        className={clsx(
          "group flex w-full items-center gap-2 py-2 text-left",
          "transition-colors duration-[120ms]",
          "hover:[@media(hover:hover)and(pointer:fine)]:text-text"
        )}
      >
        <ChevronRight
          aria-hidden="true"
          className={clsx(
            "h-3.5 w-3.5 shrink-0 text-muted",
            "transition-transform duration-200 ease-out motion-reduce:transition-none",
            open && "rotate-90"
          )}
        />
        <span className="min-w-0 flex-1 text-section font-semibold text-text">{label}</span>
        {meta ? <span className="shrink-0 text-label text-muted">{meta}</span> : null}
      </button>

      <div className="disclosure" data-open={open} role="region" id={panelId} aria-labelledby={triggerId}>
        <div>
          <div className={clsx("pb-1 transition-opacity duration-200 ease-out", open ? "opacity-100" : "opacity-0")}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

import React from "react";

interface ScreenHeaderProps {
  /** The destination's own name, as the rail says it. */
  title: string;
  /** One sentence: what this screen answers. */
  description?: React.ReactNode;
  /** Controls that belong to the screen as a whole. */
  actions?: React.ReactNode;
}

/**
 * The top of a destination.
 *
 * One pattern for all four screens: the name in the display face at a size
 * that reads from the back of a room, one sentence under it, and the screen's
 * own controls on the right. The focal figure is the strip beneath, whose
 * first tile leads — not a second headline competing with this one.
 */
export function ScreenHeader({ title, description, actions }: ScreenHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 pb-2">
      <div className="min-w-0">
        <h1 className="font-display text-[clamp(2.25rem,3.6vw,3rem)] leading-[1.02] tracking-[-0.02em] text-text">
          {title}
        </h1>
        {description ? (
          <p className="mt-3 max-w-prose-measure text-body leading-relaxed text-muted">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

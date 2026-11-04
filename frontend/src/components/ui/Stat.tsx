"use client";

import React, { useCallback, useRef } from "react";
import { clsx } from "clsx";
import { useCountUp } from "@/lib/useCountUp";
import { useTilt } from "@/lib/useTilt";
import {
  DisplayFigure,
  formatFigure,
  ChangePair,
  formatScalar,
  isIntervalTuple,
  formatInterval,
  humanizeKey,
  MISSING_DASH,
} from "@/lib/format";

/**
 * Headline figures. See frontend/DESIGN.md §5.
 *
 * The group is ONE container split by 1px dividers into equal columns — not a
 * card per figure, no icon in a tinted circle, no sparkline, no tinted tile.
 *
 * Nothing here computes. Every value arrives already decided by the API; these
 * components only choose how to present it, and always keep the exact value
 * reachable through `title`.
 */

export interface StatItem {
  /** The metric key as the API sent it, used for units and polarity. */
  metricKey: string;
  /** The untouched API value, so callers can match it against a result row. */
  raw?: unknown;
  label: string;
  /** Already-formatted value, or null when the figure is absent. */
  figure: DisplayFigure | null;
  /** Uncertainty the API supplied, rendered beside the number. */
  interval?: string | null;
  /** The period or scope this figure covers. */
  scope?: string | null;
  /** A change the API supplied both sides of. Never derived. */
  change?: ChangePair | null;
  /** Why the figure is absent, when it is. */
  absentReason?: "missing" | "not-evaluated";
  /** Opens the evidence panel at whatever produced this figure. */
  onReveal?: () => void;
  /** Names the source, e.g. "SQL query" or "churn engine". */
  sourceLabel?: string;
}

const POLARITY: Record<ChangePair["polarity"], string> = {
  positive: "text-positive",
  negative: "text-negative",
  neutral: "text-muted",
};

function StatBody({ item, lead }: { item: StatItem; lead: boolean }) {
  const { figure, absentReason } = item;

  const valueRef = useRef<HTMLSpanElement>(null);
  const formatForCount = useCallback(
    (value: number) => formatFigure(value, item.metricKey).display,
    [item.metricKey]
  );
  useCountUp(
    valueRef,
    typeof item.raw === "number" ? item.raw : null,
    figure?.display ?? "",
    formatForCount
  );

  return (
    <>
      <p className="label-caps">{item.label}</p>

      {figure ? (
        <p
          className={clsx(
            "num-display",
            // The lead figure is the screen's focal point: display scale, and
            // gold with a specular band across it rather than a flat swatch.
            lead ? "gold-foil text-display font-bold" : "text-figure-sm font-medium text-text"
          )}
          title={figure.abbreviated ? `Exact value: ${figure.exact}` : undefined}
        >
          {/* Rendered at its true value, then counted up by direct DOM writes.
              Tabular figures mean counting never reflows the line. */}
          <span ref={valueRef}>{figure.display}</span>
          {figure.unit ? (
            <span className="ml-1.5 align-baseline text-label font-normal text-muted">{figure.unit}</span>
          ) : null}
        </p>
      ) : (
        /* Three honest states, never N/A, undefined or an empty tile. */
        <p className={clsx("text-muted", lead ? "text-figure-sm" : "text-section")}>
          {absentReason === "not-evaluated" ? (
            <span className="text-body text-faint">Not evaluated</span>
          ) : (
            <span className="num-display text-faint" title="No value was returned for this metric">
              {MISSING_DASH}
            </span>
          )}
        </p>
      )}

      {item.interval ? (
        <p className="num-display text-label text-muted">95% CI {item.interval}</p>
      ) : null}

      {item.change && item.change.polarity !== undefined ? (
        <p className={clsx("flex items-baseline gap-1 text-label", POLARITY[item.change.polarity])}>
          {item.change.glyph ? <span aria-hidden="true">{item.change.glyph}</span> : null}
          <span className="num-display font-medium">{item.change.text}</span>
          {item.change.against ? <span className="text-muted">{item.change.against}</span> : null}
        </p>
      ) : null}

      {item.scope ? (
        <>
          {lead ? <span aria-hidden="true" className="rule-fade mt-1 block h-px w-full max-w-[12rem]" /> : null}
          <p className="text-label text-faint">{item.scope}</p>
        </>
      ) : null}
    </>
  );
}

/**
 * One figure. When `onReveal` is given the whole tile is a button that opens the
 * evidence panel at the SQL or engine that produced it — the provenance link.
 */
export function Stat({ item, lead = false }: { item: StatItem; lead?: boolean }) {
  const content = <StatBody item={item} lead={lead} />;
  const tilt = useTilt(2.5);

  if (!item.onReveal) {
    return <div className="min-w-0 space-y-2 px-5 py-5">{content}</div>;
  }

  return (
    <button
      type="button"
      onClick={item.onReveal}
      onPointerMove={tilt.onPointerMove}
      onPointerLeave={tilt.onPointerLeave}
      aria-label={`${item.label}: show the ${item.sourceLabel ?? "evidence"} that produced this figure`}
      title={`Show the ${item.sourceLabel ?? "evidence"} behind this figure`}
      className={clsx(
        "tilt specular group relative isolate min-w-0 space-y-2 px-5 py-5 text-left",
        "transition-[background-color,box-shadow] duration-[120ms] ease-out",
        "hover:[@media(hover:hover)and(pointer:fine)]:bg-raised active:scale-[0.99] motion-reduce:active:scale-100"
      )}
    >
      {content}
      {/* The affordance is shown on hover and on focus; repeating it under
          every figure at rest turns a quiet strip into a column of links. */}
      <span
        aria-hidden="true"
        className={clsx(
          "block text-label text-faint underline decoration-[var(--control)] underline-offset-2",
          "opacity-0 transition-opacity duration-[140ms] ease-out",
          "group-hover:[@media(hover:hover)and(pointer:fine)]:opacity-100 group-focus-visible:opacity-100"
        )}
      >
        {item.sourceLabel ? `Show ${item.sourceLabel}` : "Show evidence"}
      </span>
    </button>
  );
}

/**
 * The divided container. The column count matches the item count so no cell is
 * orphaned; on a phone it folds to two columns, and a lone trailing cell spans
 * the full width rather than sitting beside an empty half-row.
 */
export function StatGroup({
  items,
  leadFirst = true,
  className,
}: {
  items: StatItem[];
  leadFirst?: boolean;
  className?: string;
}) {
  if (items.length === 0) return null;

  const columns = Math.min(items.length, 4);
  // A lone figure hugs its content rather than stretching a card across the
  // canvas with nothing in the rest of it.
  const gridClass =
    columns === 1
      ? "grid-cols-1 sm:w-fit sm:min-w-[15rem]"
      : columns === 2
        ? "grid-cols-2"
        : columns === 3
          ? "grid-cols-2 sm:grid-cols-3"
          : "grid-cols-2 lg:grid-cols-4";

  return (
    <div
      className={clsx(
        "plane-raised grid overflow-hidden",
        "divide-x divide-y divide-[var(--rule)] [&>*]:-ml-px [&>*]:-mt-px",
        gridClass,
        className
      )}
    >
      {items.map((item, i) => (
        <Stat
          key={`${item.metricKey}-${i}`}
          item={item}
          lead={leadFirst && i === 0}
        />
      ))}
    </div>
  );
}

/**
 * Builds stat items from a KPI object.
 *
 * Measured against live payloads, `kpis` is not uniformly numeric: it holds
 * scalars, strings, [lo, hi] intervals and nested objects of metrics. Scalars
 * and strings become tiles; intervals attach to their metric; nested objects
 * are returned separately so the caller can render them as grouped key/value
 * blocks rather than forcing them into a tile or dumping JSON.
 */
export function splitKpis(kpis: Record<string, unknown>): {
  tiles: StatItem[];
  groups: { title: string; entries: { label: string; value: DisplayFigure }[] }[];
} {
  const tiles: StatItem[] = [];
  const groups: { title: string; entries: { label: string; value: DisplayFigure }[] }[] = [];

  for (const [key, value] of Object.entries(kpis ?? {})) {
    if (value === null || value === undefined) {
      tiles.push({ metricKey: key, raw: null, label: humanizeKey(key), figure: null, absentReason: "missing" });
      continue;
    }

    if (isIntervalTuple(value)) {
      tiles.push({
        metricKey: key,
        raw: value[0],
        label: humanizeKey(key),
        figure: formatScalar(value[0], key),
        interval: formatInterval(value, key),
      });
      continue;
    }

    if (typeof value === "object" && !Array.isArray(value)) {
      const entries = Object.entries(value as Record<string, unknown>)
        .filter(([, v]) => typeof v === "number" || typeof v === "string" || typeof v === "boolean")
        .map(([k, v]) => ({ label: humanizeKey(k), value: formatScalar(v, k) }));
      if (entries.length > 0) groups.push({ title: humanizeKey(key), entries });
      continue;
    }

    if (Array.isArray(value)) continue; // rendered as a table by the evidence panel

    tiles.push({ metricKey: key, raw: value, label: humanizeKey(key), figure: formatScalar(value, key) });
  }

  return { tiles, groups };
}

/** A nested metric group: a small titled key/value block, never a JSON dump. */
export function StatGroupBlock({
  title,
  entries,
}: {
  title: string;
  entries: { label: string; value: DisplayFigure }[];
}) {
  return (
    <div className="rounded-card border border-[var(--border)] bg-surface">
      <p className="border-b border-[var(--rule)] px-3.5 py-2 text-label font-medium text-text">{title}</p>
      <dl className="divide-y divide-[var(--rule)]">
        {entries.map((e) => (
          <div key={e.label} className="flex items-baseline justify-between gap-4 px-3.5 py-2">
            <dt className="min-w-0 text-label text-muted">{e.label}</dt>
            <dd
              className="num shrink-0 text-body text-text"
              title={e.value.abbreviated ? `Exact value: ${e.value.exact}` : undefined}
            >
              {e.value.display}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

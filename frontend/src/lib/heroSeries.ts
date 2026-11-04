/**
 * The series the hero is built from.
 *
 * The hero is not decoration with a data theme: every point in the scene is
 * one row of the opening query's own result, placed the way a chart places a
 * mark. Nothing here computes a figure — it chooses a category column and a
 * measure column, formats each value with the shared formatter, and names the
 * rows that hold the highest and lowest values so they can be labelled. The
 * highest value on screen is a row the API returned, not an aggregate this
 * file worked out.
 *
 * See frontend/DESIGN.md §8b.
 */

import { ChartSpecification, QueryExecutionResult } from "@/types/api";
import { formatFigure, humanizeKey } from "./format";
import { formatPeriodLabel, looksLikePeriod } from "./narrative";

export interface HeroPoint {
  /** The category as the API sent it, e.g. `2025-01`. */
  key: string;
  /** How a reader would say it, e.g. `January 2025`. */
  label: string;
  /** The axis tick, e.g. `Jan`. */
  tick: string;
  /** The API's own number, untouched. */
  value: number;
  /** The formatted figure, e.g. `$126.1M`. */
  display: string;
  /** The exact unrounded value, always one hover away. */
  exact: string;
  /** 0 at the lowest value in the series, 1 at the highest. */
  unit: number;
}

export interface HeroSeries {
  points: HeroPoint[];
  /** The measure's human name, from the result's own column. */
  measure: string;
  /** The span the rows cover, e.g. `January 2025 to December 2025`. */
  range: string | null;
  /** The rows holding the highest and the lowest value. */
  peak: HeroPoint;
  trough: HeroPoint;
  /** One sentence naming what the scene shows, for the accessible name. */
  description: string;
}

const MONTH_TICKS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** A short axis tick for a category, without inventing anything. */
function tickFor(key: string): string {
  const ym = /^(\d{4})-(\d{2})$/.exec(key.trim());
  if (ym) {
    const month = MONTH_TICKS[Number(ym[2]) - 1];
    if (month) return month;
  }
  if (/^\d{4}$/.test(key.trim())) return key.trim();
  const period = formatPeriodLabel(key);
  if (period) return period.length <= 8 ? period : period.slice(0, 7) + "…";
  return key.length <= 8 ? key : key.slice(0, 7) + "…";
}

/**
 * Builds the hero's series from a query result, or returns null when the
 * result is not a series the scene can honestly stand for: fewer than three
 * rows, no numeric measure, or no category to put on the axis.
 */
export function heroSeriesFrom(
  queryResult: QueryExecutionResult | null | undefined,
  chartSpec: ChartSpecification | null | undefined
): HeroSeries | null {
  if (!queryResult || queryResult.rows.length < 3) return null;

  const rows = queryResult.rows;

  const numericColumn =
    (chartSpec?.y_axis_field && rows.every((r) => typeof r[chartSpec.y_axis_field as string] === "number")
      ? chartSpec.y_axis_field
      : null) ?? queryResult.columns.find((c) => rows.every((r) => typeof r[c] === "number"));
  if (!numericColumn) return null;

  const categoryColumn =
    (chartSpec?.x_axis_field && rows.every((r) => typeof r[chartSpec.x_axis_field as string] === "string")
      ? chartSpec.x_axis_field
      : null) ??
    queryResult.columns.find((c) => c !== numericColumn && rows.every((r) => looksLikePeriod(String(r[c] ?? "")))) ??
    queryResult.columns.find((c) => c !== numericColumn && rows.every((r) => typeof r[c] === "string"));
  if (!categoryColumn) return null;

  const values = rows.map((r) => r[numericColumn] as number);
  const lowest = Math.min(...values);
  const highest = Math.max(...values);
  const spread = highest - lowest || 1;

  const points: HeroPoint[] = rows.map((row, i) => {
    const key = String(row[categoryColumn] ?? "");
    const value = values[i];
    const figure = formatFigure(value, numericColumn);
    return {
      key,
      label: formatPeriodLabel(key) ?? key,
      tick: tickFor(key),
      value,
      display: figure.display,
      exact: figure.exact,
      unit: (value - lowest) / spread,
    };
  });

  const peak = points.reduce((a, b) => (b.value > a.value ? b : a), points[0]);
  const trough = points.reduce((a, b) => (b.value < a.value ? b : a), points[0]);
  const measure = humanizeKey(numericColumn);

  const range =
    points[0].label === points[points.length - 1].label
      ? points[0].label
      : `${points[0].label} to ${points[points.length - 1].label}`;

  return {
    points,
    measure,
    range,
    peak,
    trough,
    description: `${measure}, ${range}. ${points.length} values from the warehouse, highest ${peak.display} in ${peak.label}, lowest ${trough.display} in ${trough.label}.`,
  };
}

/**
 * Where a point sits in the scene, in the same -1..1 space the orthographic
 * camera renders and the label layer is positioned in — so a DOM label lands
 * exactly on the point it names.
 */
export const PLOT = { left: -0.84, right: 0.86, baseline: -0.66, top: 0.74 };

export function plotX(index: number, count: number): number {
  if (count <= 1) return (PLOT.left + PLOT.right) / 2;
  return PLOT.left + (index / (count - 1)) * (PLOT.right - PLOT.left);
}

export function plotY(unit: number): number {
  // A floor under the lowest value, so the lowest point is a mark and not the
  // axis itself.
  const padded = 0.08 + unit * 0.92;
  return PLOT.baseline + padded * (PLOT.top - PLOT.baseline);
}

/** The same point as a percentage of the canvas, for the DOM label layer. */
export function plotPercent(x: number, y: number): { left: string; top: string } {
  return { left: `${((x + 1) / 2) * 100}%`, top: `${((1 - y) / 2) * 100}%` };
}

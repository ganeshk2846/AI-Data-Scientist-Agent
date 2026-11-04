/**
 * Display-only formatting for verified figures.
 *
 * The single rule this module exists to enforce: NOTHING here computes,
 * re-aggregates, infers or rounds away a value. Every function takes a number
 * the API returned and decides how to *present* it. The two presentation acts
 * that lose information — abbreviating a magnitude, and attaching a unit — both
 * carry the exact original alongside them so the precise value is always one
 * hover away and always present in full in the evidence table.
 *
 * See frontend/DESIGN.md §0 and §5.
 */

/** A value that has been prepared for display without being altered. */
export interface DisplayFigure {
  /** What is painted on screen, e.g. "$36.8M" or "0.5199". */
  display: string;
  /** The full, unrounded value as the API sent it, for `title` and the table. */
  exact: string;
  /** True when `display` is a lossy abbreviation of `exact`. */
  abbreviated: boolean;
  /** A unit suffix rendered smaller and greyer beside the value, e.g. "USD". */
  unit: string | null;
}

/** The three honest states a figure slot can be in. */
export type FigureState = "value" | "zero" | "missing" | "not-evaluated";

const MISSING_DASH = "—"; // em dash

/**
 * Counts the decimal places the parsed number actually carries, so a figure is
 * re-rendered with separators at exactly its own precision — never padded to a
 * fixed width, never rounded shorter.
 */
function decimalsOf(value: number): number {
  if (!Number.isFinite(value)) return 0;
  const s = String(value);
  if (s.includes("e") || s.includes("E")) return 0;
  const dot = s.indexOf(".");
  return dot === -1 ? 0 : s.length - dot - 1;
}

/** Groups digits at the figure's own precision. Never rounds. */
function group(value: number, decimals = decimalsOf(value)): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

const USD_KEY = /(_usd$|^revenue|_revenue$|revenue_at_risk|historical_spend|_spend$|exposure|_amount$|total_amount)/i;
const PERCENT_KEY = /(_pct$|_percentage$|percent|_rate_pct$)/i;
const COUNT_KEY = /(_count$|^count_|_customers$|customers$|^total_customers|records$|rows$)/i;

/** True when the metric's name marks it as a USD money field. */
export function isCurrencyKey(key: string): boolean {
  return USD_KEY.test(key);
}

/** True when the metric's name marks it as an already-scaled percentage. */
export function isPercentKey(key: string): boolean {
  return PERCENT_KEY.test(key);
}

/** True when the metric's name marks it as a whole-number count. */
export function isCountKey(key: string): boolean {
  return COUNT_KEY.test(key);
}

/**
 * Metrics whose good direction is DOWN. Used so a change is coloured by whether
 * it is good or bad, never by whether it points up or down. A metric not listed
 * here and not obviously "more is better" renders its change in grey.
 */
const LOWER_IS_BETTER =
  /(churn|risk|latency|error|failure|cost|drop|decline|loss|attrition|inactive|dormant|overdue|breach|delay|duration_ms|_ms$)/i;
const HIGHER_IS_BETTER = /(revenue|sales|profit|margin|orders|customers|active|retention|conversion|growth|spend)/i;

/** Which direction counts as good for this metric, or null when unknown. */
export function goodDirectionOf(key: string): "up" | "down" | null {
  if (LOWER_IS_BETTER.test(key)) return "down";
  if (HIGHER_IS_BETTER.test(key)) return "up";
  return null;
}

/**
 * Turns a raw API number into a display figure.
 *
 * Abbreviation applies only at a million and above, which is where printing
 * every digit stops being readable; below that the value is shown in full with
 * separators. `exact` always carries the untouched value.
 */
export function formatFigure(value: number, key = ""): DisplayFigure {
  if (!Number.isFinite(value)) {
    return { display: MISSING_DASH, exact: String(value), abbreviated: false, unit: null };
  }

  const currency = isCurrencyKey(key);
  const percent = isPercentKey(key);
  const count = isCountKey(key);

  const exactGrouped = group(value, count ? 0 : decimalsOf(value));
  const exact = currency ? `$${exactGrouped}` : percent ? `${exactGrouped}%` : exactGrouped;

  if (percent) {
    return { display: `${exactGrouped}%`, exact, abbreviated: false, unit: null };
  }

  const magnitude = Math.abs(value);
  if (magnitude >= 1_000_000) {
    const units: [number, string][] = [
      [1_000_000_000_000, "T"],
      [1_000_000_000, "B"],
      [1_000_000, "M"],
    ];
    const hit = units.find(([threshold]) => magnitude >= threshold);
    if (hit) {
      const [threshold, suffix] = hit;
      const scaled = value / threshold;
      const short = `${scaled.toFixed(1)}${suffix}`;
      return {
        display: currency ? `$${short}` : short,
        exact,
        abbreviated: true,
        unit: currency ? "USD" : null,
      };
    }
  }

  return {
    display: currency ? `$${exactGrouped}` : exactGrouped,
    exact,
    abbreviated: false,
    unit: currency ? "USD" : null,
  };
}

/**
 * Renders any KPI value the API may send. Measured against live payloads these
 * are numbers, strings, booleans, [lo, hi] intervals and nested objects — so
 * this never assumes "object of numbers".
 */
export function formatScalar(value: unknown, key = ""): DisplayFigure {
  if (value === null || value === undefined) {
    return { display: MISSING_DASH, exact: MISSING_DASH, abbreviated: false, unit: null };
  }
  if (typeof value === "number") return formatFigure(value, key);
  if (typeof value === "boolean") {
    return { display: value ? "Yes" : "No", exact: String(value), abbreviated: false, unit: null };
  }
  const text = String(value);
  return { display: text.length > 0 ? text : MISSING_DASH, exact: text, abbreviated: false, unit: null };
}

/** Formats a `[low, high]` interval the API supplied, e.g. confidence_interval_95. */
export function formatInterval(bounds: readonly number[], key = ""): string | null {
  if (!Array.isArray(bounds) || bounds.length < 2) return null;
  const [low, high] = bounds;
  if (typeof low !== "number" || typeof high !== "number") return null;
  if (!Number.isFinite(low) || !Number.isFinite(high)) return null;
  return `${formatFigure(low, key).display} to ${formatFigure(high, key).display}`;
}

/** True when a value is a `[low, high]` pair of finite numbers. */
export function isIntervalTuple(value: unknown): value is [number, number] {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    value.every((v) => typeof v === "number" && Number.isFinite(v))
  );
}

/** A change the API supplied both sides of. Never derived here. */
export interface ChangePair {
  /** Signed text including the sign, e.g. "+12.4%" or "-1,204". */
  text: string;
  /** Good / bad / neutral — never up / down. */
  polarity: "positive" | "negative" | "neutral";
  /** The direction glyph, so colour is never the only channel. */
  glyph: "▲" | "▼" | "";
  /** The baseline named in words, e.g. "vs prior 30 days". */
  against: string | null;
}

/**
 * Presents a change the backend already computed.
 *
 * `delta` must be a value the API returned. This function never subtracts two
 * numbers to produce one. A zero or non-finite change is neutral and grey,
 * never a signal.
 */
export function formatChange(delta: number, key = "", against: string | null = null): ChangePair {
  if (!Number.isFinite(delta) || delta === 0) {
    return {
      text: delta === 0 ? `0${isPercentKey(key) ? "%" : ""}` : MISSING_DASH,
      polarity: "neutral",
      glyph: "",
      against,
    };
  }

  const rising = delta > 0;
  const magnitude = formatFigure(Math.abs(delta), key);
  const text = `${rising ? "+" : "−"}${magnitude.display}`;
  const good = goodDirectionOf(key);

  let polarity: ChangePair["polarity"] = "neutral";
  if (good === "up") polarity = rising ? "positive" : "negative";
  else if (good === "down") polarity = rising ? "negative" : "positive";

  return { text, polarity, glyph: rising ? "▲" : "▼", against };
}

/** Milliseconds as a duration, for trace steps and timings. */
export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms)) return MISSING_DASH;
  // A sub-millisecond gap printed as "0.05 ms" reads as a broken timer rather
  // than as a step that took no measurable time.
  if (ms > 0 && ms < 1) return "under 1 ms";
  if (ms < 1000) return `${group(ms, ms < 10 ? 2 : 0)} ms`;
  const seconds = ms / 1000;
  return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;
}

/** A confidence in 0..1 as a percentage, at the precision it arrived with. */
export function formatConfidence(value: number): string {
  if (!Number.isFinite(value)) return MISSING_DASH;
  const asPercent = value <= 1 ? value * 100 : value;
  return `${Number(asPercent.toFixed(1))}%`;
}

/** Turns `total_revenue_at_risk` into `Total revenue at risk`. */
export function humanizeKey(key: string): string {
  const spaced = key.replace(/[_-]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").trim();
  if (spaced.length === 0) return key;
  return spaced.charAt(0).toUpperCase() + spaced.slice(1).toLowerCase();
}

/** A table cell: numbers right-aligned and tabular, text left, missing as a dash. */
export function formatCell(value: unknown, column = ""): { text: string; numeric: boolean; exact: string } {
  if (value === null || value === undefined || value === "") {
    return { text: MISSING_DASH, numeric: false, exact: MISSING_DASH };
  }
  if (typeof value === "number") {
    const f = formatFigure(value, column);
    return { text: f.abbreviated ? f.exact : f.display, numeric: true, exact: f.exact };
  }
  if (typeof value === "boolean") return { text: value ? "Yes" : "No", numeric: false, exact: String(value) };
  if (Array.isArray(value)) {
    const interval = formatInterval(value, column);
    if (interval) return { text: interval, numeric: true, exact: JSON.stringify(value) };
    return { text: value.join(", "), numeric: false, exact: JSON.stringify(value) };
  }
  if (typeof value === "object") {
    const json = JSON.stringify(value);
    return { text: json, numeric: false, exact: json };
  }
  const text = String(value);
  return { text, numeric: false, exact: text };
}

export { MISSING_DASH };

/**
 * The file name of a database path, for display.
 *
 * Handles both separators: the backend reports a native path, which on Windows
 * is backslash-separated.
 */
export function databaseName(path: string | null | undefined): string | null {
  if (!path) return null;
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : path;
}

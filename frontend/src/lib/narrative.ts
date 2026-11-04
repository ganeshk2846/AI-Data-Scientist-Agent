/**
 * Turning the backend's developer-facing text into something a business
 * reader can use — without changing a single value.
 *
 * Everything here is presentation: choosing which sentence to lead with,
 * humanising a key, formatting a date, attaching a currency symbol. No value
 * is computed, summed, rounded away or inferred. Where the backend gave a
 * figure, that figure is what appears.
 *
 * See frontend/DESIGN.md §6.
 */

import { QueryExecutionResult, ChartSpecification } from "@/types/api";
import { formatFigure, humanizeKey, isCurrencyKey } from "./format";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/**
 * Renders a period-shaped string as a reader would say it.
 * `2025-01` → `January 2025`; `2025-01-15` → `15 January 2025`; `2025-Q1` →
 * `Q1 2025`. Anything that is not a recognisable period comes back unchanged.
 */
export function formatPeriodLabel(value: string): string | null {
  const text = value.trim();

  const ymd = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (ymd) {
    const month = MONTHS[Number(ymd[2]) - 1];
    if (month) return `${Number(ymd[3])} ${month} ${ymd[1]}`;
  }

  const ym = /^(\d{4})-(\d{2})$/.exec(text);
  if (ym) {
    const month = MONTHS[Number(ym[2]) - 1];
    if (month) return `${month} ${ym[1]}`;
  }

  const quarter = /^(\d{4})[-\s]?Q([1-4])$/i.exec(text);
  if (quarter) return `Q${quarter[2]} ${quarter[1]}`;

  const week = /^(\d{4})-W(\d{1,2})$/i.exec(text);
  if (week) return `Week ${Number(week[2])}, ${week[1]}`;

  if (/^\d{4}$/.test(text)) return text;

  return null;
}

/** True when a string reads as a period rather than a plain category. */
export function looksLikePeriod(value: string): boolean {
  return formatPeriodLabel(value) !== null && /\d{4}/.test(value);
}

/** One humanised field from a raw `key: value` fragment. */
export interface HumanField {
  label: string;
  value: string;
  /** True when the field reads as the row's scope rather than a measure. */
  isScope: boolean;
}

const NOISE_PREFIX = /^(data observation|observation|row|record|result|note|detail)s?\s*:\s*/i;

/**
 * Parses a raw `key: value, key: value` line into humanised fields.
 *
 * The composer emits lines such as
 * `Data observation: month: 2025-01, total_revenue: 64830335.73`.
 * That is a developer dump; a reader wants `January 2025 · $64,830,335.73`.
 * Returns null when the line is ordinary prose and should be left alone.
 */
export function parseKeyValueLine(line: string): HumanField[] | null {
  const text = line.replace(NOISE_PREFIX, "").trim();
  if (!text) return null;

  const parts = text.split(/,\s+(?=[A-Za-z_][A-Za-z0-9_ ]*\s*:)/);
  const fields: HumanField[] = [];

  for (const part of parts) {
    const match = /^([A-Za-z_][A-Za-z0-9_ ]*)\s*:\s*(.+)$/.exec(part.trim());
    if (!match) return null;

    const key = match[1].trim();
    const raw = match[2].trim();
    // A key with spaces and several words is prose, not a field name.
    if (key.split(/\s+/).length > 3) return null;

    const period = formatPeriodLabel(raw);
    if (period) {
      fields.push({ label: humanizeKey(key), value: period, isScope: true });
      continue;
    }

    const asNumber = Number(raw.replace(/,/g, ""));
    if (raw !== "" && Number.isFinite(asNumber) && /^-?[\d,]*\.?\d+$/.test(raw)) {
      fields.push({ label: humanizeKey(key), value: formatFigure(asNumber, key).display, isScope: false });
      continue;
    }

    fields.push({ label: humanizeKey(key), value: raw, isScope: !isCurrencyKey(key) });
  }

  // A single field is not a key/value dump worth restructuring.
  return fields.length >= 2 ? fields : null;
}

/** Renders humanised fields as one readable line: scope first, then measures. */
export function renderHumanFields(fields: HumanField[]): string {
  const scopes = fields.filter((f) => f.isScope).map((f) => f.value);
  const measures = fields.filter((f) => !f.isScope);
  const left = scopes.join(" · ");
  const right = measures
    .map((m) => (measures.length === 1 ? m.value : `${m.label} ${m.value}`))
    .join(" · ");
  return [left, right].filter(Boolean).join(" · ");
}

/**
 * Removes inline markdown so emphasis markers never reach the screen as
 * literal asterisks or underscores. A bare `*` surrounded by spaces (a
 * multiplication sign) is left alone.
 */
export function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*\*(.+?)\*\*\*/g, "$1")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/(^|[\s(])\*(\S(?:.*?\S)?)\*(?=[\s).,;:!?]|$)/g, "$1$2")
    .replace(/(^|[\s(])_(\S(?:.*?\S)?)_(?=[\s).,;:!?]|$)/g, "$1$2")
    .replace(/`(.+?)`/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();
}

const HEADLINE_REJECT =
  /^(query returned|returned|rows returned|result set|execution|no rows|\d+\s+rows?\b)/i;

/**
 * True when a backend headline is a developer artefact rather than a finding.
 * "Query returned 12 rows." tells a reader nothing they asked for.
 */
export function isUnusableHeadline(headline: string | null | undefined): boolean {
  if (!headline) return true;
  const text = headline.trim();
  if (text.length === 0) return true;
  return HEADLINE_REJECT.test(text);
}

/**
 * The first real sentence of a narrative.
 *
 * Skips markdown headings, table rows, dividers, and bare bold labels such as
 * `**Direct Answer**`, which carry no finding. Returns null when the narrative
 * is entirely tabular — which is common, and is why callers need a fallback.
 */
export function firstSentence(markdown: string | null | undefined): string | null {
  if (!markdown) return null;

  for (const rawLine of markdown.replace(/\r\n/g, "\n").split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    if (line.startsWith("|") || line.startsWith("#") || /^[-=*_]{3,}$/.test(line)) continue;

    const plain = stripMarkdown(line.replace(/^[-*•]\s+/, ""));

    if (!plain) continue;
    // A bare label such as "Direct Answer" is not a sentence.
    if (plain.split(/\s+/).length < 4) continue;
    if (parseKeyValueLine(plain)) continue;

    const sentence = /^(.+?[.!?])(\s|$)/.exec(plain);
    const candidate = (sentence ? sentence[1] : plain).trim();
    if (candidate.split(/\s+/).length < 4) continue;
    return candidate;
  }

  return null;
}

/** The span a result covers, taken from its own first and last period values. */
export function periodRange(queryResult: QueryExecutionResult | null | undefined): string | null {
  if (!queryResult || queryResult.rows.length === 0) return null;

  for (const column of queryResult.columns) {
    const values = queryResult.rows
      .map((r) => r[column])
      .filter((v): v is string => typeof v === "string");
    if (values.length !== queryResult.rows.length) continue;
    if (!values.every(looksLikePeriod)) continue;

    const sorted = [...values].sort();
    const first = formatPeriodLabel(sorted[0]);
    const last = formatPeriodLabel(sorted[sorted.length - 1]);
    if (!first || !last) continue;
    return first === last ? first : `${first} to ${last}`;
  }

  return null;
}

/** The human name of the measure a result reports, from its own columns. */
export function measureName(
  queryResult: QueryExecutionResult | null | undefined,
  chartSpec: ChartSpecification | null | undefined
): string | null {
  if (chartSpec?.y_axis_field) return humanizeKey(chartSpec.y_axis_field);
  if (!queryResult) return null;
  const numeric = queryResult.columns.find((c) =>
    queryResult.rows.some((r) => typeof r[c] === "number")
  );
  return numeric ? humanizeKey(numeric) : null;
}

/**
 * A headline for a section whose own headline is unusable.
 *
 * Describes the shape of the result — which measure, over which span, across
 * how many rows — using only values the backend returned. It never states a
 * total, an average or a trend, because none of those were sent.
 */
export function describeResult(
  queryResult: QueryExecutionResult | null | undefined,
  chartSpec: ChartSpecification | null | undefined,
  fallback: string
): string {
  const measure = measureName(queryResult, chartSpec);
  const range = periodRange(queryResult);
  const rows = queryResult?.row_count ?? 0;

  if (measure && range) return `${measure}, ${range}`;
  if (measure && rows > 1) return `${measure} across ${rows.toLocaleString("en-US")} rows`;
  if (measure) return measure;
  if (chartSpec?.title) return chartSpec.title;
  return fallback;
}

/**
 * Finds the row a single KPI value came from, so a figure that is one row of a
 * many-row result can be labelled with that row's scope instead of reading as
 * a total the backend never sent.
 */
export function scopeForValue(
  value: unknown,
  queryResult: QueryExecutionResult | null | undefined
): string | null {
  if (typeof value !== "number" || !queryResult || queryResult.rows.length < 2) return null;

  const matches = queryResult.rows.filter((row) =>
    Object.values(row).some((v) => typeof v === "number" && v === value)
  );
  if (matches.length !== 1) return null;

  const row = matches[0];
  for (const column of queryResult.columns) {
    const cell = row[column];
    if (typeof cell !== "string") continue;
    const period = formatPeriodLabel(cell);
    if (period) return period;
    if (cell.length <= 40) return cell;
  }
  return null;
}

/**
 * True when the result is a series — many rows of one measure — and so should
 * lead with its chart rather than with one figure lifted out of it.
 */
export function isSeriesResult(
  queryResult: QueryExecutionResult | null | undefined,
  chartSpec: ChartSpecification | null | undefined
): boolean {
  if (!queryResult || queryResult.row_count < 2) return false;
  if (chartSpec && chartSpec.chart_type !== "table" && !chartSpec.fallback_to_table) return true;
  return queryResult.row_count >= 3 && queryResult.columns.length <= 3;
}

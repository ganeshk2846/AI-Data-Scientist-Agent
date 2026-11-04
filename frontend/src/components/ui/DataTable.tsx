"use client";

import React from "react";
import { clsx } from "clsx";
import { formatCell, humanizeKey } from "@/lib/format";

interface DataTableProps {
  columns: string[];
  rows: Record<string, unknown>[];
  /** Shown above the table, e.g. "12 rows". */
  caption?: React.ReactNode;
  /** The API's own truncation flag — never inferred from row count. */
  truncated?: boolean;
  /** Names the window queried, for the empty state. */
  emptyMessage?: string;
  maxHeight?: string;
  className?: string;
}

/**
 * Rules and alignment, not decoration: 12px grey sentence-case headers, no fill
 * band, no zebra striping, numbers right-aligned in tabular figures, a real
 * zero printed and a missing value as a grey dash.
 *
 * The table scrolls inside its own frame with a sticky header, so the page
 * never scrolls sideways on a phone.
 */
export function DataTable({
  columns,
  rows,
  caption,
  truncated = false,
  emptyMessage = "No rows matched this query.",
  maxHeight = "26rem",
  className,
}: DataTableProps) {
  const numericColumn = React.useMemo(
    () =>
      columns.map((col) =>
        rows.length > 0 &&
        rows.every((row) => {
          const v = row[col];
          return v === null || v === undefined || v === "" || typeof v === "number";
        }) &&
        rows.some((row) => typeof row[col] === "number")
      ),
    [columns, rows]
  );

  if (columns.length === 0) {
    return (
      <p className="rounded-card border border-dashed border-[var(--border)] px-3 py-6 text-center text-body text-muted">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className={clsx("space-y-2", className)}>
      {caption ? <p className="text-label text-muted">{caption}</p> : null}

      <div
        className="scroll-quiet overflow-auto rounded-card border border-[var(--border)]"
        style={{ maxHeight }}
      >
        <table className="w-full border-collapse text-body">
          <thead className="sticky top-0 z-10 bg-surface">
            <tr>
              {columns.map((col, c) => (
                <th
                  key={col}
                  scope="col"
                  className={clsx(
                    "whitespace-nowrap border-b border-[var(--border)] bg-surface px-4 py-3 last:pr-5",
                    "label-caps font-medium",
                    numericColumn[c] ? "text-right" : "text-left"
                  )}
                >
                  {humanizeKey(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-body text-muted">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              rows.map((row, r) => (
                <tr key={r} className="row-responds border-b border-[var(--rule)] last:border-0">
                  {columns.map((col, c) => {
                    const cell = formatCell(row[col], col);
                    return (
                      <td
                        key={col}
                        title={cell.text !== cell.exact ? cell.exact : undefined}
                        className={clsx(
                          "px-4 py-3 align-top last:pr-5",
                          numericColumn[c] || cell.numeric
                            ? "num whitespace-nowrap text-right text-text"
                            : "text-left text-text"
                        )}
                      >
                        {cell.text}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {truncated ? (
        <p className="text-label text-muted">
          The backend truncated this result set. The rows above are what it returned.
        </p>
      ) : null}
    </div>
  );
}

import React from "react";
import { clsx } from "clsx";
import { CopyButton } from "./CopyButton";

/**
 * SQL, highlighted and copyable.
 *
 * The highlighter tokenises rather than regex-replacing into HTML, so the SQL
 * is rendered as React text nodes and can never inject markup. Colour here is
 * the one place ink alone would cost legibility: keywords take the muted tier,
 * strings and numbers the data hue — well under the screen's colour budget.
 */

const KEYWORDS = new Set(
  `SELECT FROM WHERE GROUP BY ORDER HAVING LIMIT OFFSET JOIN LEFT RIGHT INNER OUTER FULL CROSS ON AS AND OR NOT IN IS NULL LIKE BETWEEN CASE WHEN THEN ELSE END DISTINCT UNION ALL WITH ASC DESC COUNT SUM AVG MIN MAX ROUND COALESCE CAST STRFTIME DATE SUBSTR OVER PARTITION`
    .split(/\s+/)
);

const TOKENISER = /(\s+|--[^\n]*|'(?:[^']|'')*'|"(?:[^"]|"")*"|\b\d+(?:\.\d+)?\b|\w+|[^\w\s])/g;

function Highlighted({ sql }: { sql: string }) {
  const tokens = sql.match(TOKENISER) ?? [sql];
  return (
    <>
      {tokens.map((token, i) => {
        if (/^\s+$/.test(token)) return <React.Fragment key={i}>{token}</React.Fragment>;
        if (token.startsWith("--")) {
          return (
            <span key={i} className="text-faint italic">
              {token}
            </span>
          );
        }
        if (token.startsWith("'") || token.startsWith('"')) {
          return (
            <span key={i} style={{ color: "var(--series-1)" }}>
              {token}
            </span>
          );
        }
        if (/^\d/.test(token)) {
          return (
            <span key={i} style={{ color: "var(--series-1)" }}>
              {token}
            </span>
          );
        }
        if (KEYWORDS.has(token.toUpperCase())) {
          return (
            <span key={i} className="font-medium text-muted">
              {token}
            </span>
          );
        }
        return <React.Fragment key={i}>{token}</React.Fragment>;
      })}
    </>
  );
}

interface SqlBlockProps {
  sql: string;
  /** Names this query, e.g. "Query 2 of 3". */
  label?: string;
  copyLabel?: string;
  className?: string;
}

export function SqlBlock({ sql, label, copyLabel = "SQL", className }: SqlBlockProps) {
  return (
    <div className={clsx("overflow-hidden rounded-card border border-[var(--border)] bg-surface", className)}>
      <div className="flex items-center justify-between gap-2 border-b border-[var(--rule)] py-1 pl-3 pr-1">
        <span className="text-label text-muted">{label ?? "SQL executed"}</span>
        <CopyButton value={sql} label={copyLabel} />
      </div>
      <pre className="scroll-quiet overflow-x-auto px-3 py-3 text-[13px] leading-relaxed">
        <code className="font-mono text-text">
          <Highlighted sql={sql} />
        </code>
      </pre>
    </div>
  );
}

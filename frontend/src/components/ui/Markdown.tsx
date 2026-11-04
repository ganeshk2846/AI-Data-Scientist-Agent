import React from "react";
import { clsx } from "clsx";
import { parseKeyValueLine, renderHumanFields } from "@/lib/narrative";

/**
 * A small markdown renderer for the subset the composer actually emits:
 * headings, paragraphs, bullet and ordered lists, pipe tables, bold, and
 * inline code.
 *
 * It builds React elements directly. Nothing is ever passed to
 * `dangerouslySetInnerHTML`, so model-authored text cannot inject markup.
 * Figures inside tables are right-aligned and set in the tabular mono face so
 * a markdown table of numbers lines up digit for digit like a real one.
 */

const BOLD_OR_CODE = /(\*\*[^*]+\*\*|`[^`]+`)/g;
const NUMERIC_CELL = /^[-+$(]?\s*[\d,]+(\.\d+)?\s*%?\)?$/;

/** Renders bold and inline-code spans inside a line of text. */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split(BOLD_OR_CODE).filter(Boolean).map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return (
        <strong key={key} className="font-semibold text-text">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code key={key} className="rounded-chip bg-raised px-1 py-0.5 font-mono text-[0.92em]">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={key}>{part}</React.Fragment>;
  });
}

function splitRow(line: string): string[] {
  return line.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());
}

function isDividerRow(line: string): boolean {
  return /^\s*\|?[\s:-]*-[\s|:-]*\|?\s*$/.test(line) && line.includes("-");
}

export function Markdown({ content, className }: { content: string; className?: string }) {
  if (!content || content.trim().length === 0) return null;

  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];

  let paragraph: string[] = [];
  let bullets: string[] = [];
  let ordered: string[] = [];

  function flushParagraph() {
    if (paragraph.length === 0) return;
    const key = `p-${blocks.length}`;
    const joined = paragraph.join(" ");
    const fields = parseKeyValueLine(joined);
    blocks.push(
      <p key={key} className="text-body text-text">
        {fields ? renderHumanFields(fields) : renderInline(joined, key)}
      </p>
    );
    paragraph = [];
  }

  function flushBullets() {
    if (bullets.length === 0) return;
    const key = `ul-${blocks.length}`;
    blocks.push(
      <ul key={key} className="space-y-1.5 text-body text-text">
        {bullets.map((item, i) => {
          /* A raw `key: value, key: value` dump is restructured into a
             readable line; ordinary prose passes through untouched. */
          const fields = parseKeyValueLine(item);
          if (fields) {
            const scope = fields.filter((f) => f.isScope).map((f) => f.value).join(" · ");
            const measures = fields.filter((f) => !f.isScope);
            return (
              <li
                key={`${key}-${i}`}
                className="flex items-baseline justify-between gap-4 border-b border-[var(--rule)] pb-1.5 last:border-0"
              >
                <span className="min-w-0 text-text">{scope || renderHumanFields(fields)}</span>
                {measures.length > 0 ? (
                  <span className="num-display shrink-0 font-medium text-text">
                    {measures.map((m) => m.value).join(" · ")}
                  </span>
                ) : null}
              </li>
            );
          }
          return (
            <li key={`${key}-${i}`} className="flex gap-2.5">
              <span aria-hidden="true" className="mt-[0.6em] h-1 w-1 shrink-0 rounded-full bg-[var(--control)]" />
              <span className="min-w-0 flex-1">{renderInline(item, `${key}-${i}`)}</span>
            </li>
          );
        })}
      </ul>
    );
    bullets = [];
  }

  function flushOrdered() {
    if (ordered.length === 0) return;
    const key = `ol-${blocks.length}`;
    blocks.push(
      <ol key={key} className="space-y-1.5 text-body text-text">
        {ordered.map((item, i) => (
          <li key={`${key}-${i}`} className="flex gap-2.5">
            <span className="num mt-px w-4 shrink-0 text-right text-label text-muted">{i + 1}.</span>
            <span className="min-w-0 flex-1">{renderInline(item, `${key}-${i}`)}</span>
          </li>
        ))}
      </ol>
    );
    ordered = [];
  }

  function flushAll() {
    flushParagraph();
    flushBullets();
    flushOrdered();
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.length === 0) {
      flushAll();
      continue;
    }

    // Pipe table: a header row followed by a divider row.
    if (trimmed.startsWith("|") && i + 1 < lines.length && isDividerRow(lines[i + 1])) {
      flushAll();
      const header = splitRow(trimmed);
      const rows: string[][] = [];
      let j = i + 2;
      while (j < lines.length && lines[j].trim().startsWith("|")) {
        rows.push(splitRow(lines[j].trim()));
        j++;
      }
      const numericColumn = header.map((_, col) =>
        rows.length > 0 && rows.every((r) => !r[col] || NUMERIC_CELL.test(r[col]))
      );
      const key = `table-${blocks.length}`;
      blocks.push(
        <div key={key} className="scroll-quiet -mx-1 overflow-x-auto px-1">
          <table className="w-full border-collapse text-body">
            <thead>
              <tr>
                {header.map((cell, c) => (
                  <th
                    key={`${key}-h-${c}`}
                    scope="col"
                    className={clsx(
                      "whitespace-nowrap border-b border-[var(--border)] px-2.5 py-2 text-label font-normal text-muted last:pr-4",
                      numericColumn[c] ? "text-right" : "text-left"
                    )}
                  >
                    {cell}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={`${key}-r-${r}`} className="border-b border-[var(--rule)] last:border-0">
                  {header.map((_, c) => (
                    <td
                      key={`${key}-r-${r}-${c}`}
                      className={clsx(
                        "px-2.5 py-2 align-top last:pr-4",
                        numericColumn[c] ? "num text-right text-text" : "text-left text-text"
                      )}
                    >
                      {renderInline(row[c] ?? "", `${key}-r-${r}-${c}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      i = j - 1;
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(trimmed);
    if (heading) {
      flushAll();
      const key = `h-${blocks.length}`;
      blocks.push(
        <p key={key} className="text-section font-semibold text-text">
          {renderInline(heading[2], key)}
        </p>
      );
      continue;
    }

    const bullet = /^[-*•]\s+(.*)$/.exec(trimmed);
    if (bullet) {
      flushParagraph();
      flushOrdered();
      bullets.push(bullet[1]);
      continue;
    }

    const numbered = /^\d+[.)]\s+(.*)$/.exec(trimmed);
    if (numbered) {
      flushParagraph();
      flushBullets();
      ordered.push(numbered[1]);
      continue;
    }

    flushBullets();
    flushOrdered();
    paragraph.push(trimmed);
  }

  flushAll();

  return <div className={clsx("space-y-3", className)}>{blocks}</div>;
}

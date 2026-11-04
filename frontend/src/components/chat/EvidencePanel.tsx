"use client";

import React from "react";
import { clsx } from "clsx";
import { Check, AlertTriangle } from "lucide-react";
import { MultiAgentWorkflowResult } from "@/types/api";
import { DataTable } from "@/components/ui/DataTable";
import { SqlBlock } from "@/components/ui/SqlBlock";
import { Disclosure } from "@/components/ui/Disclosure";
import { Badge } from "@/components/ui/Badge";
import {
  formatCell,
  formatConfidence,
  formatInterval,
  formatScalar,
  humanizeKey,
  isIntervalTuple,
} from "@/lib/format";

/** A labelled block inside the panel. Keeps its frame even when empty. */
function Block({
  title,
  note,
  children,
  id,
}: {
  title: string;
  note?: React.ReactNode;
  children: React.ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className="space-y-2 scroll-mt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h4 className="text-label font-medium text-text">{title}</h4>
        {note ? <span className="text-label text-muted">{note}</span> : null}
      </div>
      {children}
    </section>
  );
}

/** The honest empty state for a block that has nothing to show. */
function Nothing({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded-card border border-dashed border-[var(--border)] px-3 py-3 text-body text-muted">
      {children}
    </p>
  );
}

function KeyValueRows({ entries }: { entries: { label: string; value: string; exact?: string }[] }) {
  return (
    <dl className="overflow-hidden rounded-card border border-[var(--border)] divide-y divide-[var(--rule)]">
      {entries.map((e) => (
        <div key={e.label} className="flex items-baseline justify-between gap-4 px-3.5 py-2">
          <dt className="min-w-0 text-body text-muted">{e.label}</dt>
          <dd
            className="num shrink-0 text-right text-body text-text"
            title={e.exact && e.exact !== e.value ? `Exact value: ${e.exact}` : undefined}
          >
            {e.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * Renders `computed_metrics`, which is not a flat map: measured against live
 * payloads it mixes scalars, `[lo, hi]` intervals and arrays of objects (the
 * churn engine returns ten segment records under one key). Scalars become
 * rows, arrays become real tables, nested objects become titled sub-blocks.
 * Nothing is ever printed as raw JSON.
 */
function ComputedMetrics({ metrics }: { metrics: Record<string, unknown> }) {
  const scalars: { label: string; value: string; exact?: string }[] = [];
  const tables: { title: string; columns: string[]; rows: Record<string, unknown>[] }[] = [];
  const nested: { title: string; entries: { label: string; value: string; exact?: string }[] }[] = [];

  for (const [key, value] of Object.entries(metrics ?? {})) {
    if (value === null || value === undefined) {
      scalars.push({ label: humanizeKey(key), value: "—" });
      continue;
    }
    if (isIntervalTuple(value)) {
      scalars.push({ label: humanizeKey(key), value: formatInterval(value, key) ?? "—" });
      continue;
    }
    if (Array.isArray(value)) {
      const objectRows = value.filter(
        (v): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v)
      );
      if (objectRows.length > 0) {
        const columns = Array.from(new Set(objectRows.flatMap((r) => Object.keys(r))));
        tables.push({ title: humanizeKey(key), columns, rows: objectRows });
      } else if (value.length > 0) {
        scalars.push({ label: humanizeKey(key), value: value.map((v) => String(v)).join(", ") });
      }
      continue;
    }
    if (typeof value === "object") {
      const entries = Object.entries(value as Record<string, unknown>).map(([k, v]) => {
        const f = formatScalar(v, k);
        return { label: humanizeKey(k), value: f.display, exact: f.exact };
      });
      if (entries.length > 0) nested.push({ title: humanizeKey(key), entries });
      continue;
    }
    const f = formatScalar(value, key);
    scalars.push({ label: humanizeKey(key), value: f.display, exact: f.exact });
  }

  if (scalars.length === 0 && tables.length === 0 && nested.length === 0) {
    return <Nothing>This run recorded no computed metrics.</Nothing>;
  }

  return (
    <div className="space-y-3">
      {scalars.length > 0 ? <KeyValueRows entries={scalars} /> : null}
      {nested.map((n) => (
        <div key={n.title} className="space-y-1.5">
          <p className="text-label text-muted">{n.title}</p>
          <KeyValueRows entries={n.entries} />
        </div>
      ))}
      {tables.map((t) => (
        <div key={t.title} className="space-y-1.5">
          <p className="text-label text-muted">{t.title}</p>
          <DataTable columns={t.columns} rows={t.rows} maxHeight="22rem" />
        </div>
      ))}
    </div>
  );
}

function Chips({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <li key={item}>
          <Badge variant="neutral" className="font-mono">
            {item}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

export const EVIDENCE_SQL_ANCHOR = "evidence-sql";

interface EvidencePanelProps {
  result: MultiAgentWorkflowResult;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /**
   * The figure whose provenance link opened the panel. Naming it here is the
   * shared element between the tile and the panel: the figure the reader
   * clicked becomes the panel's heading, so the move is legible.
   */
  openedBy?: string | null;
  className?: string;
}

/**
 * Everything behind the answer, in one disclosure.
 *
 * This is the product's whole credibility claim, so each block is designed
 * rather than dumped: the SQL is highlighted and copyable, the rows are a real
 * table, and a block with nothing in it says so plainly instead of rendering
 * an empty frame.
 */
export function EvidencePanel({ result, open, onOpenChange, openedBy, className }: EvidencePanelProps) {
  const analytical = result.analytical_result ?? null;
  const executed = analytical?.executed_queries ?? [];
  const queryResult = result.query_result ?? null;
  const verification = result.verification ?? null;
  const limitations = [...(result.limitations ?? []), ...(analytical?.limitations ?? [])];

  /** Names what is actually in the panel, rather than a count of unnamed things. */
  const sources: string[] = [];
  if (result.sanitized_sql) sources.push("SQL");
  if (executed.length > 0) sources.push(`${executed.length} queries`);
  if (queryResult) sources.push(`${queryResult.row_count} rows`);
  if (analytical && Object.keys(analytical.computed_metrics ?? {}).length > 0) sources.push("computed metrics");
  if (verification) sources.push("checks");
  const sourceSummary = sources.length > 0 ? sources.join(" · ") : "Nothing was recorded for this run";

  return (
    <div className={clsx("plane-float px-5", className)}>
      <Disclosure
        open={open}
        onOpenChange={onOpenChange}
        label="Evidence"
        meta={open ? "Everything behind this answer" : sourceSummary}
      >
        <div className={clsx("space-y-6 pb-4 pt-1", open && "flip-open")}>
          {openedBy ? (
            <p className="arrive rounded-card border border-[var(--accent-edge)] bg-accent-soft px-3.5 py-2.5 text-body text-text">
              Showing what produced <span className="font-semibold">{openedBy}</span>.
            </p>
          ) : null}
          {/* 1 — the SQL */}
          <Block title="SQL executed" id={EVIDENCE_SQL_ANCHOR}>
            {result.sanitized_sql ? (
              <SqlBlock sql={result.sanitized_sql} label="Validated, read-only" />
            ) : (
              <Nothing>
                No SQL was recorded for this run
                {result.specialist_capability
                  ? ` — the ${result.specialist_capability.replace(/_/g, " ")} engine produced the figures directly.`
                  : "."}
              </Nothing>
            )}
          </Block>

          {/* 2 — specialist queries */}
          {executed.length > 0 ? (
            <Block title="Queries run by the specialist workflow" note={`${executed.length} in total`}>
              <div className="space-y-2">
                {executed.map((sql, i) => (
                  <SqlBlock
                    key={i}
                    sql={sql}
                    label={`Query ${i + 1} of ${executed.length}`}
                    copyLabel={`query ${i + 1}`}
                  />
                ))}
              </div>
            </Block>
          ) : null}

          {/* 3 — computed metrics */}
          {analytical ? (
            <Block title="Computed metrics">
              <ComputedMetrics metrics={analytical.computed_metrics ?? {}} />
            </Block>
          ) : null}

          {/* 4 — method and confidence */}
          {analytical ? (
            <Block title="Method">
              <div className="space-y-2.5">
                {analytical.selected_methods && analytical.selected_methods.length > 0 ? (
                  <Chips items={analytical.selected_methods} />
                ) : (
                  <Nothing>No named method was recorded for this run.</Nothing>
                )}
                {typeof analytical.confidence_score === "number" ? (
                  <KeyValueRows
                    entries={[
                      { label: "Confidence score", value: formatConfidence(analytical.confidence_score) },
                    ]}
                  />
                ) : null}
                {analytical.uncertainty_notes && analytical.uncertainty_notes.length > 0 ? (
                  <ul className="space-y-1.5 text-body text-text">
                    {analytical.uncertainty_notes.map((note, i) => (
                      <li key={i}>{note}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </Block>
          ) : null}

          {/* 5 — the rows */}
          <Block
            title="Rows returned"
            note={
              queryResult
                ? `${queryResult.row_count} row${queryResult.row_count === 1 ? "" : "s"} in ${queryResult.execution_time_ms.toFixed(0)} ms`
                : undefined
            }
          >
            {queryResult ? (
              <DataTable
                columns={queryResult.columns}
                rows={queryResult.rows}
                truncated={queryResult.truncated}
                emptyMessage="The query ran and matched no rows."
              />
            ) : (
              <Nothing>This run did not execute a row-returning query.</Nothing>
            )}
          </Block>

          {/* 6 — verification */}
          <Block title="Verification">
            {verification ? (
              <div className="space-y-2">
                {verification.checks_passed.length > 0 ? (
                  <ul className="space-y-1">
                    {verification.checks_passed.map((check) => (
                      <li key={check} className="flex items-baseline gap-2 text-body text-text">
                        <Check aria-hidden="true" className="mt-[0.2em] h-3.5 w-3.5 shrink-0 text-positive" />
                        {check}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Nothing>No verification checks were recorded.</Nothing>
                )}

                {verification.warnings.length > 0 ? (
                  <ul className="space-y-1">
                    {verification.warnings.map((warning, i) => (
                      <li key={i} className="flex items-baseline gap-2 text-body text-text">
                        <AlertTriangle aria-hidden="true" className="mt-[0.2em] h-3.5 w-3.5 shrink-0 text-warning" />
                        {warning}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-body text-muted">No warnings were raised.</p>
                )}

                {verification.empty_result ? (
                  <p className="text-body text-text">The query completed and returned an empty result.</p>
                ) : null}
              </div>
            ) : (
              <Nothing>This run recorded no verification result.</Nothing>
            )}
          </Block>

          {/* 7 — limitations */}
          {limitations.length > 0 ? (
            <Block title="Limitations">
              <ul className="space-y-1.5 text-body text-text">
                {limitations.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </Block>
          ) : null}

          {/* 8 — the planned DAG */}
          {result.plan && result.plan.steps.length > 0 ? (
            <Block
              title="Planned steps"
              note="The plan the agent drew up — see “How this was answered” for what actually ran"
            >
              <ol className="overflow-hidden rounded-card border border-[var(--border)] divide-y divide-[var(--rule)]">
                {result.plan.steps.map((step, i) => (
                  <li key={step.step_id} className="flex items-baseline gap-3 px-3.5 py-2">
                    <span className="num w-5 shrink-0 text-right text-label text-muted">{i + 1}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-body text-text">{step.description}</span>
                      <span className="block font-mono text-label text-muted">{step.tool_name}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </Block>
          ) : null}

          {/* 9 — tables consulted */}
          {result.selected_tables.length > 0 ? (
            <Block title="Tables consulted">
              <Chips items={result.selected_tables} />
            </Block>
          ) : null}

          {/* 10 — value linking */}
          {result.linked_values.length > 0 ? (
            <Block title="Values matched to the database" note="How wording in the question was resolved">
              <DataTable
                columns={["user_mention", "exact_db_value", "target_table", "target_column", "confidence"]}
                rows={result.linked_values.map((v) => ({ ...v }))}
                maxHeight="18rem"
              />
            </Block>
          ) : null}

          {/* 11 — repairs */}
          {result.repair_attempts.length > 0 ? (
            <Block title="Repair attempts" note={`${result.repair_attempts.length} made`}>
              <div className="space-y-3">
                {result.repair_attempts.map((attempt) => (
                  <div key={attempt.attempt_number} className="space-y-2">
                    <p className="text-body text-text">
                      Attempt {attempt.attempt_number}:{" "}
                      <span className={attempt.success ? "text-positive" : "text-negative"}>
                        {attempt.success ? "succeeded" : "failed"}
                      </span>
                      . {attempt.explanation}
                    </p>
                    <p className="text-label text-muted">{attempt.error_message}</p>
                    <SqlBlock
                      sql={attempt.repaired_sql}
                      label={`Repaired SQL, attempt ${attempt.attempt_number}`}
                      copyLabel="repaired SQL"
                    />
                  </div>
                ))}
              </div>
            </Block>
          ) : null}

          {/* 12 — provenance of the run itself */}
          <Block title="Run">
            <KeyValueRows
              entries={[
                { label: "Run id", value: result.run_id },
                { label: "Session", value: result.session_id },
                ...(result.standalone_query && result.standalone_query !== result.query
                  ? [{ label: "Read as", value: result.standalone_query }]
                  : []),
                {
                  label: "Intent",
                  value: `${result.route.intent} · ${formatConfidence(result.route.confidence)} confidence`,
                },
                { label: "Complexity", value: result.route.complexity },
                ...(analytical?.analysis_id
                  ? [{ label: "Analysis id", value: String(analytical.analysis_id) }]
                  : []),
              ].map((e) => ({ ...e, value: formatCell(e.value).text }))}
            />
          </Block>
        </div>
      </Disclosure>
    </div>
  );
}

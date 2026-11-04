"use client";

import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import { fetchSchemaStatus, fetchTableDetail, fetchTables, fetchBusinessMetrics } from "@/lib/api";
import { Badge } from "./ui/Badge";
import { Disclosure } from "./ui/Disclosure";
import { SqlBlock } from "./ui/SqlBlock";
import { StatGroup, StatItem } from "./ui/Stat";
import { formatFigure, MISSING_DASH } from "@/lib/format";
import { ScreenHeader } from "./ui/ScreenHeader";

/**
 * The Catalog: what tables exist, what is in them, and the metric definitions
 * the agent grounds against.
 *
 * A list beside a detail pane — the list is the index, the pane answers "what
 * is in this table". On a phone the pane follows the list rather than sitting
 * beside it.
 */
export function SchemaReadinessSection() {
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"tables" | "metrics">("tables");

  const { data: status } = useQuery({ queryKey: ["schemaStatus"], queryFn: fetchSchemaStatus });
  const { data: tables, isLoading: loadingTables } = useQuery({ queryKey: ["tables"], queryFn: fetchTables });
  const { data: metrics, isLoading: loadingMetrics } = useQuery({
    queryKey: ["businessMetrics"],
    queryFn: fetchBusinessMetrics,
    enabled: view === "metrics",
  });

  const activeTable = selected ?? tables?.[0]?.name ?? null;

  const { data: detail, isLoading: loadingDetail } = useQuery({
    queryKey: ["tableDetail", activeTable],
    queryFn: () => (activeTable ? fetchTableDetail(activeTable) : null),
    enabled: Boolean(activeTable),
  });

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return tables ?? [];
    return (tables ?? []).filter((t) => t.name.toLowerCase().includes(term));
  }, [tables, search]);

  const summary = status?.catalog_summary;
  const tiles: StatItem[] = summary
    ? [
        {
          metricKey: "total_rows",
          raw: summary.total_rows,
          label: "Rows catalogued",
          figure: formatFigure(summary.total_rows, "total_rows"),
          scope: summary.generated_at ? `Prepared ${new Date(summary.generated_at).toLocaleDateString()}` : null,
        },
        {
          metricKey: "total_tables",
          raw: summary.total_tables,
          label: "Tables",
          figure: formatFigure(summary.total_tables, "total_tables"),
        },
      ]
    : [];

  return (
    <div className="space-y-10">
      <ScreenHeader
        title="Data"
        description={
          status?.is_prepared
            ? "Every table the agent can see, the columns inside them, and the metric definitions it is grounded against."
            : "The schema has not been prepared yet, so the agent has nothing to ground against."
        }
        actions={
          <div
            role="group"
            aria-label="What to show"
            className="flex items-center gap-0.5 rounded-control border border-[var(--border)] bg-surface p-1 shadow-raised"
          >
            {(["tables", "metrics"] as const).map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={view === v}
                onClick={() => setView(v)}
                className={clsx(
                  "h-8 rounded-[5px] px-3.5 text-label capitalize",
                  "transition-[background-color,color] duration-[90ms] ease-out",
                  view === v
                    ? "bg-active font-medium text-text"
                    : "text-muted hover:[@media(hover:hover)and(pointer:fine)]:text-accent"
                )}
              >
                {v}
              </button>
            ))}
          </div>
        }
      />

      {tiles.length > 0 ? <StatGroup items={tiles} /> : null}

      {view === "metrics" ? (
        <section className="space-y-2">
          <h2 className="text-section font-semibold text-text">Metric definitions</h2>
          {loadingMetrics ? (
            <ul className="space-y-1.5" aria-label="Loading metrics">
              {[0, 1, 2].map((i) => (
                <li key={i} className="skeleton h-[52px] w-full rounded-card" />
              ))}
            </ul>
          ) : !metrics || metrics.length === 0 ? (
            <p className="rounded-card border border-dashed border-[var(--border)] px-3 py-8 text-center text-body text-muted">
              No business metrics are defined for this database.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {metrics.map((metric) => (
                <li key={metric.name} className="responds plane-raised px-4">
                  <Disclosure label={metric.display_name} meta={metric.primary_tables.join(", ")}>
                    <div className="space-y-2.5 pb-3">
                      <p className="text-body text-text">{metric.plain_description}</p>
                      <SqlBlock sql={metric.formula_sql} label="Definition" copyLabel="metric SQL" />
                      {metric.business_caveat ? (
                        <p className="text-body text-warning">{metric.business_caveat}</p>
                      ) : null}
                    </div>
                  </Disclosure>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]">
          {/* The index */}
          <section className="space-y-2" aria-label="Tables">
            <label htmlFor="table-search" className="sr-only">
              Search tables
            </label>
            <input
              id="table-search"
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tables"
              className="h-9 w-full rounded-control border border-[var(--control)] bg-surface px-3 text-body text-text placeholder:text-faint focus:border-[var(--text)] focus:outline-none"
            />

            {loadingTables ? (
              <ul className="space-y-1" aria-label="Loading tables">
                {Array.from({ length: 8 }, (_, i) => (
                  <li key={i} className="skeleton h-[36px] w-full rounded-control" />
                ))}
              </ul>
            ) : filtered.length === 0 ? (
              <p className="rounded-card border border-dashed border-[var(--border)] px-3 py-6 text-center text-body text-muted">
                No table matches “{search}”.
              </p>
            ) : (
              <ul className="scroll-quiet max-h-[32rem] space-y-0.5 overflow-y-auto">
                {filtered.map((table) => {
                  const isActive = table.name === activeTable;
                  return (
                    <li key={table.name}>
                      <button
                        type="button"
                        onClick={() => setSelected(table.name)}
                        aria-current={isActive ? "true" : undefined}
                        className={clsx(
                          "row-responds flex w-full items-baseline justify-between gap-2 rounded-control px-3 py-2.5 text-left",
                          isActive ? "bg-active text-text" : "text-text"
                        )}
                      >
                        <span className="min-w-0 truncate font-mono text-body">{table.name}</span>
                        <span className="num shrink-0 text-label text-muted">
                          {table.row_count.toLocaleString("en-US")}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* The detail */}
          <section aria-label="Table detail" className="min-w-0 space-y-3">
            {loadingDetail || !detail ? (
              <div className="rounded-card border border-[var(--border)] bg-surface p-4">
                <span className="skeleton block h-[18px] w-40" />
                <span className="skeleton mt-3 block h-[14px] w-full" />
                <span className="skeleton mt-2 block h-[14px] w-5/6" />
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="font-mono text-headline font-semibold text-text">{detail.name}</h2>
                  <p className="num text-label text-muted">
                    {detail.row_count.toLocaleString("en-US")} rows · {detail.columns.length} columns
                  </p>
                </div>

                {detail.description ? <p className="text-body text-muted">{detail.description}</p> : null}

                <div className="scroll-quiet overflow-x-auto rounded-card border border-[var(--border)]">
                  <table className="w-full border-collapse text-body">
                    <thead>
                      <tr>
                        {["Column", "Type", "Nulls", "Distinct", "Example"].map((h, i) => (
                          <th
                            key={h}
                            scope="col"
                            className={clsx(
                              "whitespace-nowrap border-b border-[var(--border)] bg-surface px-3 py-2.5 text-label font-normal text-muted last:pr-4",
                              i >= 2 && i <= 3 ? "text-right" : "text-left"
                            )}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {detail.columns.map((column) => (
                        <tr key={column.name} className="row-responds border-b border-[var(--rule)] last:border-0">
                          <td className="px-3 py-2.5 last:pr-4">
                            <span className="font-mono text-body text-text">{column.name}</span>
                            <span className="ml-2 inline-flex gap-1 align-middle">
                              {column.is_pk ? <Badge variant="neutral">PK</Badge> : null}
                              {column.is_fk ? (
                                <Badge variant="neutral" title={`References ${column.fk_target_table}.${column.fk_target_column}`}>
                                  FK
                                </Badge>
                              ) : null}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 font-mono text-label text-muted last:pr-4">{column.sqlite_type}</td>
                          <td className="num px-3 py-2.5 text-right text-text last:pr-4">
                            {column.null_percentage.toFixed(1)}%
                          </td>
                          <td className="num px-3 py-2.5 text-right text-text last:pr-4">
                            {column.distinct_count.toLocaleString("en-US")}
                          </td>
                          {/* The truncation lives on a block inside the cell:
                              max-width on a <td> is advisory and the table
                              layout overrides it, so a long sample ran 202px
                              past the frame and was clipped rather than
                              ellipsised. */}
                          <td className="px-3 py-2.5 pr-4 text-muted">
                            {column.sample_values.length > 0 ? (
                              <span
                                className="block max-w-[14rem] truncate"
                                title={column.sample_values[0]}
                              >
                                {column.sample_values[0]}
                              </span>
                            ) : (
                              <span className="text-faint">{MISSING_DASH}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {detail.foreign_keys.length > 0 ? (
                  <div className="space-y-1.5">
                    <h3 className="text-label font-medium text-text">Relationships</h3>
                    <ul className="space-y-1">
                      {detail.foreign_keys.map((fk) => (
                        <li key={`${fk.source_column}-${fk.target_table}`} className="font-mono text-label text-muted">
                          {fk.source_column} → {fk.target_table}.{fk.target_column}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

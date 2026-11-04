"use client";

import React from "react";
import { ReadinessStatus } from "@/types/api";
import { Button } from "./ui/Button";
import { Notice } from "./ui/Notice";
import { StatGroup, StatItem } from "./ui/Stat";
import { formatFigure } from "@/lib/format";
import { ScreenHeader } from "./ui/ScreenHeader";

interface HealthReadinessCardProps {
  data?: ReadinessStatus;
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  onRefresh: () => void;
}

function Row({ label, value, note }: { label: string; value: React.ReactNode; note?: string }) {
  return (
    <div className="row-responds flex items-baseline justify-between gap-4 px-4 py-3">
      <dt className="min-w-0 text-body text-muted">
        {label}
        {note ? <span className="mt-0.5 block text-label text-faint">{note}</span> : null}
      </dt>
      <dd className="shrink-0 text-right text-body text-text">{value}</dd>
    </div>
  );
}

function State({ ok, yes, no }: { ok: boolean; yes: string; no: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-positive" : "bg-negative"}`}
      />
      {ok ? yes : no}
    </span>
  );
}

/**
 * The System screen: is everything connected, and is the database genuinely
 * read-only.
 *
 * The loading state is the final layout with each value replaced by a flat bar
 * at its real size, so nothing shifts when the data lands.
 */
export function HealthReadinessCard({
  data,
  isLoading,
  isError,
  error,
  onRefresh,
}: HealthReadinessCardProps) {
  if (isLoading) {
    return (
      <div className="space-y-10">
        <ScreenHeader title="System" description="Checking the database, the model and the app store." />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="plane-raised px-5 py-5">
              <span className="skeleton block h-[11px] w-24" />
              <span className="skeleton mt-3 block h-[38px] w-32" />
            </div>
          ))}
        </div>
        <span className="sr-only">Loading system status</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-10">
        <ScreenHeader title="System" />
        <Notice
          tone="negative"
          title="The backend could not be reached"
          action={
            <Button size="sm" variant="secondary" onClick={onRefresh}>
              Try again
            </Button>
          }
        >
          {error?.message ??
            "No response from the API. Start it with: python -m uvicorn backend.app.main:app --port 8001"}
        </Notice>
      </div>
    );
  }

  const { database, llm } = data;

  const tiles: StatItem[] = [
    {
      metricKey: "table_count",
      label: "Tables",
      figure: typeof database.table_count === "number" ? formatFigure(database.table_count, "table_count") : null,
      absentReason: "not-evaluated",
    },
    {
      metricKey: "total_rows",
      label: "Rows",
      figure: typeof database.total_rows === "number" ? formatFigure(database.total_rows, "total_rows") : null,
      absentReason: "not-evaluated",
    },
    {
      metricKey: "size_bytes",
      label: "Database size",
      figure:
        typeof database.size_bytes === "number"
          ? {
              display: `${(database.size_bytes / 1_000_000).toFixed(1)} MB`,
              exact: `${database.size_bytes.toLocaleString("en-US")} bytes`,
              abbreviated: true,
              unit: null,
            }
          : null,
      absentReason: "not-evaluated",
    },
  ];

  return (
    <div className="space-y-10">
      <ScreenHeader
        title="System"
        description={
          data.ready
            ? "Connected and ready to answer questions. The warehouse is open read-only, and that is verified rather than assumed."
            : "Not ready — one of the checks below has not passed."
        }
        actions={
          <Button size="sm" variant="secondary" onClick={onRefresh}>
            Refresh
          </Button>
        }
      />

      <StatGroup items={tiles} />

      <section className="space-y-3">
        <h2 className="text-headline font-semibold text-text">Database</h2>
        <dl className="plane-raised divide-y divide-[var(--rule)] overflow-hidden">
          <Row label="Connection" value={<State ok={database.connected} yes="Connected" no="Not connected" />} />
          <Row
            label="Read-only"
            note="The agent can never write to the warehouse"
            value={<State ok={database.read_only_verified} yes="Verified" no="Not verified" />}
          />
          <Row label="Path" value={<span className="font-mono text-label">{database.path}</span>} />
          {database.error ? <Row label="Error" value={<span className="text-negative">{database.error}</span>} /> : null}
        </dl>
      </section>

      <section className="space-y-3">
        <h2 className="text-headline font-semibold text-text">Model</h2>
        <dl className="plane-raised divide-y divide-[var(--rule)] overflow-hidden">
          <Row label="Provider" value={llm.provider} />
          <Row label="Model" value={<span className="font-mono text-label">{llm.model}</span>} />
          <Row label="Configured" value={<State ok={llm.configured} yes="Yes" no="No" />} />
          <Row label="Status" value={llm.message} />
        </dl>
      </section>

      <section className="space-y-3">
        <h2 className="text-headline font-semibold text-text">Application store</h2>
        <dl className="plane-raised divide-y divide-[var(--rule)] overflow-hidden">
          <Row
            label="Sessions and traces"
            note="Threads, active frames and telemetry"
            value={<State ok={data.app_store_ready} yes="Ready" no="Unavailable" />}
          />
          <Row label="Version" value={<span className="font-mono text-label">{data.version}</span>} />
          <Row
            label="Checked"
            value={<span className="num text-label">{new Date(data.timestamp).toLocaleString()}</span>}
          />
        </dl>
      </section>
    </div>
  );
}

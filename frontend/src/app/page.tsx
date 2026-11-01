"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchReadiness } from "@/lib/api";
import { Header } from "@/components/Header";
import { HealthReadinessCard } from "@/components/HealthReadinessCard";
import { SchemaReadinessSection } from "@/components/SchemaReadinessSection";
import { Layers, Database } from "lucide-react";

export default function HomePage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    refetchInterval: 10000,
  });

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Header isReady={data?.ready} version={data?.version} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        {/* System Readiness & Connectivity Card */}
        <HealthReadinessCard
          data={data}
          isLoading={isLoading}
          isError={isError}
          error={error as Error}
          onRefresh={() => refetch()}
        />

        {/* Phase 2: Schema Preparation & Catalog Explorer */}
        <SchemaReadinessSection />

        {/* Architectural Pipeline Overview */}
        <section className="space-y-4">
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-primary" />
            <h2 className="text-base font-semibold text-foreground">
              Production Execution Pipeline
            </h2>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 text-xs">
            {[
              { step: "1. Retrieve", desc: "BM25 + Embedding RRF schema grounding" },
              { step: "2. Constrain", desc: "Allowlisted identifiers only" },
              { step: "3. Plan", desc: "Typed DAG decomposition" },
              { step: "4. Generate", desc: "Safe read-only SQL generation" },
              { step: "5. Validate", desc: "sqlglot AST validation guardrail" },
              { step: "6. Execute", desc: "Strict read-only SQLite execution" },
              { step: "7. Verify", desc: "Result sanity & claim validation" },
              { step: "8. Analyze", desc: "Deterministic stats & ML tools" },
              { step: "9. Visualize", desc: "Plotly specifications & tables" },
              { step: "10. Explain", desc: "Business narrative with citations" },
            ].map((p, i) => (
              <div
                key={i}
                className="p-3 rounded-lg border border-border bg-card/60 flex flex-col justify-between space-y-1"
              >
                <span className="font-semibold text-primary">{p.step}</span>
                <span className="text-[11px] text-muted-foreground">{p.desc}</span>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-4 px-6 text-center text-xs text-muted-foreground">
        AI for BI Data Scientist Agent — Grounded Business Intelligence
      </footer>
    </div>
  );
}

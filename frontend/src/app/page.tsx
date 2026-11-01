"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchReadiness } from "@/lib/api";
import { Header } from "@/components/Header";
import { HealthReadinessCard } from "@/components/HealthReadinessCard";
import { Layers, ShieldCheck, Terminal, BookOpen, BarChart3, Database } from "lucide-react";

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
        {/* Readiness Probe Card */}
        <HealthReadinessCard
          data={data}
          isLoading={isLoading}
          isError={isError}
          error={error as Error}
          onRefresh={() => refetch()}
        />

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

        {/* Dataset Quick Summary */}
        <section className="p-6 rounded-xl border border-border bg-card/40 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-primary" />
              <h2 className="text-base font-semibold text-foreground">
                Verified Business Warehouse Domains
              </h2>
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              30 Tables | 334,503 Rows | 2023-01-01 to 2025-12-31
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            {[
              { domain: "Customers & Segments", count: "4 tables", detail: "5,000 customers; 6 RFM tiers (VIP, Loyal, At Risk, etc.)" },
              { domain: "Orders & Transactions", count: "5 tables", detail: "17,924 orders ($21.76M gross); 30,707 order items" },
              { domain: "Merchandising & Catalog", count: "6 tables", detail: "1,000 products; 30 brands; 30 categories; 4 promos" },
              { domain: "Supply Chain & Logistics", count: "5 tables", detail: "20 warehouses; 24 suppliers; 12,960 inventory snapshots" },
              { domain: "Marketing & Web Funnel", count: "4 tables", detail: "8 channels; 8,768 spend days; 71,046 web sessions" },
              { domain: "Service, Reviews & Finance", count: "6 tables", detail: "9,224 reviews; 2,174 tickets; 6,576 expense records" },
            ].map((d, idx) => (
              <div key={idx} className="p-3 rounded-lg border border-border bg-background/50 space-y-1">
                <div className="flex justify-between font-medium text-foreground">
                  <span>{d.domain}</span>
                  <span className="text-primary font-mono text-[11px]">{d.count}</span>
                </div>
                <p className="text-[11px] text-muted-foreground">{d.detail}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-4 px-6 text-center text-xs text-muted-foreground">
        AI for BI Data Scientist Agent — Phase 1 Project Foundation
      </footer>
    </div>
  );
}

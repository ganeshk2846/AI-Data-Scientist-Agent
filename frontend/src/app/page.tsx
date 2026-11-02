"use client";

import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchReadiness } from "@/lib/api";
import { Header } from "@/components/Header";
import { HealthReadinessCard } from "@/components/HealthReadinessCard";
import { SchemaReadinessSection } from "@/components/SchemaReadinessSection";
import { ChatInterface } from "@/components/ChatInterface";
import { ObservabilityDashboard } from "@/components/ObservabilityDashboard";
import {
  Activity,
  Database,
  Layers,
  MessageSquare,
  ShieldCheck,
  Search,
  Filter,
  CheckCircle2,
  Cpu,
  BarChart2,
  FileText,
  Lock,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";

type NavigationTab = "chat" | "schema" | "observability" | "system";

const PIPELINE_STEPS = [
  { step: "1. Ground", name: "Hybrid Retrieval", desc: "BM25 + TF-IDF RRF (k=60) schema grounding & 1-hop FK graph expansion", icon: Search },
  { step: "2. Constrain", name: "Identifier Filter", desc: "Allowlists discovered table & column tokens to eliminate schema hallucinations", icon: Filter },
  { step: "3. Plan", name: "DAG Decomposition", desc: "Generates typed 7-step execution DAG with explicit dependencies", icon: Layers },
  { step: "4. Generate", name: "SQL Synthesis", desc: "Synthesizes minimal SQLite SELECT statements strictly matching prompt intent", icon: Cpu },
  { step: "5. Validate", name: "AST Guardrail", desc: "sqlglot AST inspection blocks DDL/DML with bounded 2-attempt auto-repair", icon: Lock },
  { step: "6. Execute", name: "Read-Only Runner", desc: "Executes on ecommerce.sqlite in URI mode=ro with strict row caps", icon: Database },
  { step: "7. Verify", name: "Result Verification", desc: "Validates numerical sanity, empty results, row counts, and domain bounds", icon: CheckCircle2 },
  { step: "8. Analyze", name: "Deterministic ML", desc: "Pure Python stats, MAD anomaly detection, Holt-Winters forecast, SLSQP", icon: BarChart2 },
  { step: "9. Visualize", name: "Plotly.js Renderer", desc: "Auto-derives responsive interactive chart specs with full CSV/JSON export", icon: Activity },
  { step: "10. Synthesize", name: "Executive Composer", desc: "Executive narrative with citations, coverage caveats, and 3 follow-ups", icon: FileText },
];

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<NavigationTab>("chat");

  // Sync tab with URL search parameter if present
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab") as NavigationTab;
      if (tabParam && ["chat", "schema", "observability", "system"].includes(tabParam)) {
        setActiveTab(tabParam);
      }
    }
  }, []);

  const handleTabChange = (tab: NavigationTab) => {
    setActiveTab(tab);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", tab);
      window.history.replaceState({}, "", url.toString());
    }
  };

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    refetchInterval: 15000,
  });

  const TABS = [
    {
      key: "chat" as NavigationTab,
      label: "Conversational BI",
      icon: MessageSquare,
      badge: "Active Thread",
    },
    {
      key: "schema" as NavigationTab,
      label: "Data Warehouse & Schema",
      icon: Database,
      badge: `${data?.database?.table_count ?? 30} Tables`,
    },
    {
      key: "observability" as NavigationTab,
      label: "Telemetry & Latency",
      icon: Activity,
      badge: "p50 / p95 Traces",
    },
    {
      key: "system" as NavigationTab,
      label: "System Health & Pipeline",
      icon: ShieldCheck,
      badge: data?.ready ? "Verified" : "Connecting",
    },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground selection:bg-primary/20 selection:text-primary">
      <Header isReady={data?.ready} version={data?.version} />

      {/* Modern Sticky Navigation Bar */}
      <div className="border-b border-border/80 bg-card/60 backdrop-blur-md sticky top-[61px] z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-6">
          <nav className="flex items-center space-x-1.5 sm:space-x-2 py-2.5 overflow-x-auto scrollbar-none">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => handleTabChange(tab.key)}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all duration-150 whitespace-nowrap cursor-pointer select-none ${
                    isActive
                      ? "bg-primary text-white shadow-md shadow-primary/20 ring-1 ring-primary/40"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{tab.label}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono transition-colors ${
                      isActive
                        ? "bg-white/20 text-white font-bold"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {tab.badge}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6 space-y-6">
        {/* Workspace 1: Conversational BI Assistant */}
        {activeTab === "chat" && <ChatInterface />}

        {/* Workspace 2: Data Warehouse & Schema Dictionary */}
        {activeTab === "schema" && <SchemaReadinessSection />}

        {/* Workspace 3: Telemetry & Observability Cockpit */}
        {activeTab === "observability" && <ObservabilityDashboard />}

        {/* Workspace 4: System Readiness & Architectural Pipeline */}
        {activeTab === "system" && (
          <div className="space-y-6">
            <HealthReadinessCard
              data={data}
              isLoading={isLoading}
              isError={isError}
              error={error as Error}
              onRefresh={() => refetch()}
            />

            {/* Visual Multi-Agent Pipeline Map */}
            <section className="p-6 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-border/80">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-primary/15 text-primary">
                    <Layers className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-foreground">
                      10-Stage Multi-Agent Execution Pipeline
                    </h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Deterministic orchestration guarantees strict grounding, AST safety, and non-hallucinating calculations
                    </p>
                  </div>
                </div>
                <Badge variant="success" size="xs">
                  Production Verified
                </Badge>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                {PIPELINE_STEPS.map((p, i) => {
                  const StepIcon = p.icon;
                  return (
                    <div
                      key={i}
                      className="p-4 rounded-xl border border-border/80 bg-background/50 hover:bg-muted/30 transition-all flex flex-col justify-between space-y-2 group shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] font-bold text-primary px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20">
                          {p.step}
                        </span>
                        <StepIcon className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground text-xs">{p.name}</h4>
                        <p className="text-[11px] text-muted-foreground leading-relaxed mt-1">
                          {p.desc}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/80 py-4 px-6 text-center text-xs text-muted-foreground bg-card/40 backdrop-blur">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>AI for BI Data Scientist Agent — Enterprise Conversational Business Intelligence</span>
          <div className="flex items-center gap-3 text-[11px] font-mono">
            <span>ecommerce.sqlite (mode=ro)</span>
            <span>•</span>
            <span>agent_app.sqlite (traces & frames)</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

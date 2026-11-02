"use client";

import React, { useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchSchemaStatus,
  fetchTableDetail,
  fetchTables,
  fetchBusinessMetrics,
  triggerSchemaPreparation,
} from "@/lib/api";
import { TableModel, TableSummary, BusinessMetric } from "@/types/api";
import {
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  Database,
  Hash,
  Key,
  Layers,
  Link as LinkIcon,
  Play,
  RefreshCw,
  Search,
  Table as TableIcon,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";

// Business domains mapped to warehouse tables
const DOMAIN_GROUPS: Record<string, string[]> = {
  "Orders & Sales": ["orders", "order_items", "payments", "order_timeline"],
  "Customers": ["customers", "customer_segments", "customer_segment_history", "loyalty_cards", "loyalty_transactions"],
  "Catalog & Merchandising": ["products", "product_categories", "brands", "categories", "promotions", "promotion_rules", "seller_products", "sellers"],
  "Supply Chain & Inventory": ["warehouses", "suppliers", "purchase_orders", "purchase_order_items", "warehouse_stock", "monthly_inventory_snapshot", "inbound_shipments"],
  "Marketing & Traffic": ["channels", "daily_marketing_spend", "website_sessions", "session_events"],
  "Post-Purchase & Service": ["returns", "refunds", "customer_reviews", "support_tickets"],
  "Financials & Targets": ["expenses", "daily_targets"],
};

export function SchemaReadinessSection() {
  const queryClient = useQueryClient();
  const [selectedTableName, setSelectedTableName] = useState<string>("orders");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDomain, setSelectedDomain] = useState<string>("All");
  const [activeSubTab, setActiveSubTab] = useState<"catalog" | "metrics">("catalog");

  // Query schema preparation status
  const { data: schemaStatus } = useQuery({
    queryKey: ["schemaStatus"],
    queryFn: fetchSchemaStatus,
    refetchInterval: (query) => {
      const state = query.state.data?.latest_job?.status;
      return state === "pending" || state === "running" ? 1500 : 15000;
    },
  });

  // Query tables list
  const { data: tables, isLoading: isLoadingTables } = useQuery({
    queryKey: ["schemaTables"],
    queryFn: fetchTables,
  });

  // Query selected table detail
  const { data: selectedTable, isLoading: isLoadingTableDetail } = useQuery({
    queryKey: ["tableDetail", selectedTableName],
    queryFn: () => (selectedTableName ? fetchTableDetail(selectedTableName) : null),
    enabled: !!selectedTableName,
  });

  // Query verified business metrics
  const { data: businessMetrics, isLoading: isLoadingMetrics } = useQuery({
    queryKey: ["businessMetrics"],
    queryFn: fetchBusinessMetrics,
  });

  // Prepare schema mutation
  const prepareMutation = useMutation({
    mutationFn: (force: boolean) => triggerSchemaPreparation(force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schemaStatus"] });
      queryClient.invalidateQueries({ queryKey: ["schemaTables"] });
      if (selectedTableName) {
        queryClient.invalidateQueries({ queryKey: ["tableDetail", selectedTableName] });
      }
    },
  });

  const isPreparing =
    prepareMutation.isPending ||
    schemaStatus?.latest_job?.status === "running" ||
    schemaStatus?.latest_job?.status === "pending";

  // Filtered tables based on search and domain
  const filteredTables = useMemo(() => {
    return (tables || []).filter((t) => {
      const matchesSearch = t.name.toLowerCase().includes(searchTerm.toLowerCase());
      if (!matchesSearch) return false;
      if (selectedDomain === "All") return true;
      const domainTables = DOMAIN_GROUPS[selectedDomain] || [];
      return domainTables.includes(t.name);
    });
  }, [tables, searchTerm, selectedDomain]);

  return (
    <section className="space-y-6">
      {/* 1. Header & Profiler Management Bar */}
      <div className="p-6 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-primary/15 text-primary">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold text-foreground">
                    Data Warehouse & Schema Catalog
                  </h2>
                  <Badge variant={schemaStatus?.is_prepared ? "success" : "warning"} size="xs">
                    {schemaStatus?.is_prepared ? "Catalogue Active" : "Unprepared"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Idempotent profiling of 30 tables, relational lineage, distinct distributions, and null rates
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            <Button
              variant="primary"
              size="sm"
              onClick={() => prepareMutation.mutate(false)}
              disabled={isPreparing}
              isLoading={isPreparing}
              icon={!isPreparing ? <Play className="w-3.5 h-3.5" /> : undefined}
            >
              {isPreparing ? "Profiling..." : "Run Preparation"}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => prepareMutation.mutate(true)}
              disabled={isPreparing}
              title="Force re-profiling bypasses cache"
            >
              Force Refresh
            </Button>
          </div>
        </div>

        {/* Live Progress Bar during active profiling job */}
        {isPreparing && (
          <div className="p-4 rounded-xl bg-background/70 border border-primary/30 space-y-2">
            <div className="flex justify-between text-xs">
              <span className="font-medium text-primary flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>{schemaStatus?.latest_job?.message || "Running preparation worker..."}</span>
              </span>
              <span className="font-mono text-muted-foreground">
                {schemaStatus?.latest_job?.progress_percent || 0}%
              </span>
            </div>
            <div className="w-full bg-border rounded-full h-2 overflow-hidden">
              <div
                className="bg-primary h-2 transition-all duration-300"
                style={{ width: `${schemaStatus?.latest_job?.progress_percent || 5}%` }}
              />
            </div>
          </div>
        )}

        {/* Summary Metric Ribbon */}
        {schemaStatus?.catalog_summary && !isPreparing && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-3 border-t border-border/60">
            <div className="p-2.5 rounded-xl bg-background/50 border border-border/60 flex items-center justify-between">
              <span className="text-muted-foreground">Profiled Tables:</span>
              <span className="font-bold text-foreground font-mono">
                {schemaStatus.catalog_summary.total_tables}
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-background/50 border border-border/60 flex items-center justify-between">
              <span className="text-muted-foreground">Total Warehouse Rows:</span>
              <span className="font-bold text-foreground font-mono">
                {schemaStatus.catalog_summary.total_rows.toLocaleString()}
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-background/50 border border-border/60 flex items-center justify-between">
              <span className="text-muted-foreground">Fingerprint:</span>
              <span
                className="font-mono text-primary truncate max-w-[100px]"
                title={schemaStatus.catalog_summary.source_fingerprint || ""}
              >
                {schemaStatus.catalog_summary.source_fingerprint?.slice(0, 10)}...
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-background/50 border border-border/60 flex items-center justify-between">
              <span className="text-muted-foreground">Cache State:</span>
              <span className="text-success font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Verified Fresh</span>
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 2. Sub-Tabs: Table Catalog vs Business Metrics Glossary */}
      <div className="flex items-center gap-2 border-b border-border/80 pb-2">
        <button
          type="button"
          onClick={() => setActiveSubTab("catalog")}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-2 transition-all cursor-pointer ${
            activeSubTab === "catalog"
              ? "bg-primary text-white shadow-sm"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
          }`}
        >
          <TableIcon className="w-3.5 h-3.5" />
          <span>Relational Table Catalog ({tables?.length || 0})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab("metrics")}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-2 transition-all cursor-pointer ${
            activeSubTab === "metrics"
              ? "bg-primary text-white shadow-sm"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-warning" />
          <span>Verified Business Metrics ({businessMetrics?.length || 0})</span>
        </button>
      </div>

      {/* 3. Sub-View A: Interactive Table Catalog & Inspector */}
      {activeSubTab === "catalog" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Pane: Table Selector */}
          <div className="lg:col-span-4 p-5 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-border/70">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <TableIcon className="w-4 h-4 text-primary" />
                <span>Cataloged Tables</span>
              </div>
              <Badge variant="mono" size="xs">
                {filteredTables.length} / {tables?.length || 0}
              </Badge>
            </div>

            {/* Domain Filter Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
              {["All", ...Object.keys(DOMAIN_GROUPS)].map((dom) => (
                <button
                  key={dom}
                  type="button"
                  onClick={() => setSelectedDomain(dom)}
                  className={`text-[10px] px-2 py-0.5 rounded-md whitespace-nowrap transition-colors cursor-pointer ${
                    selectedDomain === dom
                      ? "bg-primary/20 text-primary border border-primary/40 font-semibold"
                      : "bg-background/60 text-muted-foreground hover:text-foreground border border-border/60"
                  }`}
                >
                  {dom}
                </button>
              ))}
            </div>

            {/* Search Box */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-muted-foreground pointer-events-none" />
              <input
                type="text"
                placeholder="Filter tables by name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-background/60 border border-border rounded-lg text-foreground focus:outline-none focus:border-primary placeholder:text-muted-foreground/70"
              />
            </div>

            {/* Table List Scrollable Container */}
            <div className="space-y-1.5 max-h-[520px] overflow-y-auto pr-1">
              {isLoadingTables && (
                <div className="p-6 text-center text-xs text-muted-foreground">
                  <RefreshCw className="w-4 h-4 animate-spin text-primary mx-auto mb-2" />
                  <span>Loading tables from database...</span>
                </div>
              )}
              {filteredTables.map((tbl) => {
                const isSelected = selectedTableName === tbl.name;
                return (
                  <button
                    key={tbl.name}
                    type="button"
                    onClick={() => setSelectedTableName(tbl.name)}
                    className={`w-full text-left p-3 rounded-xl text-xs transition-all flex items-center justify-between cursor-pointer ${
                      isSelected
                        ? "bg-primary text-white shadow-sm font-semibold ring-1 ring-primary/40"
                        : "hover:bg-muted/50 text-foreground/90 border border-transparent hover:border-border/60"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <TableIcon
                        className={`w-3.5 h-3.5 flex-shrink-0 ${
                          isSelected ? "text-white" : "text-primary"
                        }`}
                      />
                      <span className="truncate">{tbl.name}</span>
                    </div>
                    <span
                      className={`font-mono text-[11px] flex-shrink-0 ${
                        isSelected ? "text-white/80" : "text-muted-foreground"
                      }`}
                    >
                      {tbl.row_count.toLocaleString()} rows
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Pane: Table Detail Inspector */}
          <div className="lg:col-span-8 p-6 rounded-2xl border border-border/80 bg-card/90 shadow-md space-y-5">
            {isLoadingTableDetail && (
              <div className="py-24 text-center text-xs text-muted-foreground flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="w-7 h-7 animate-spin text-primary" />
                <span>Introspecting schema profile for {selectedTableName}...</span>
              </div>
            )}

            {!isLoadingTableDetail && selectedTable && (
              <>
                {/* Table Header Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-border/80 gap-3">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h3 className="text-lg font-bold text-foreground font-mono">
                        {selectedTable.name}
                      </h3>
                      <Badge variant="primary" size="xs">
                        {selectedTable.row_count.toLocaleString()} rows
                      </Badge>
                      <Badge variant="mono" size="xs">
                        {selectedTable.columns.length} columns
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Primary Key:{" "}
                      <code className="text-foreground font-mono">
                        {selectedTable.primary_key_columns.join(", ") || "RowID"}
                      </code>{" "}
                      | Foreign Keys: {selectedTable.foreign_keys.length} | Indexes:{" "}
                      {selectedTable.indexes.length}
                    </p>
                  </div>
                </div>

                {/* Columns Table */}
                <div className="overflow-x-auto border border-border/70 rounded-xl bg-background/40">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-muted/70 text-muted-foreground font-semibold border-b border-border">
                      <tr>
                        <th className="p-3">Column</th>
                        <th className="p-3">Type</th>
                        <th className="p-3">Constraints</th>
                        <th className="p-3">Null Rate</th>
                        <th className="p-3 font-mono">Distinct</th>
                        <th className="p-3">Sample / Range</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {selectedTable.columns.map((c) => (
                        <tr key={c.name} className="hover:bg-muted/30 transition-colors">
                          <td className="p-3 font-mono text-foreground font-semibold">
                            {c.name}
                          </td>
                          <td className="p-3 font-mono text-muted-foreground">
                            {c.sqlite_type}
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {c.is_pk && (
                                <Badge variant="warning" size="xs" className="gap-0.5">
                                  <Key className="w-2.5 h-2.5" />
                                  <span>PK</span>
                                </Badge>
                              )}
                              {c.is_fk && (
                                <Badge
                                  variant="primary"
                                  size="xs"
                                  className="gap-0.5 cursor-pointer"
                                  title={`Foreign Key -> ${c.fk_target_table}.${c.fk_target_column}`}
                                  onClick={() => {
                                    if (c.fk_target_table) {
                                      setSelectedTableName(c.fk_target_table);
                                    }
                                  }}
                                >
                                  <LinkIcon className="w-2.5 h-2.5" />
                                  <span>FK</span>
                                </Badge>
                              )}
                              {c.is_date_candidate && (
                                <Badge variant="mono" size="xs" className="gap-0.5">
                                  <Calendar className="w-2.5 h-2.5" />
                                  <span>Date</span>
                                </Badge>
                              )}
                              {c.is_numeric_candidate && !c.is_pk && !c.is_fk && (
                                <Badge variant="mono" size="xs" className="gap-0.5">
                                  <Hash className="w-2.5 h-2.5" />
                                  <span>Num</span>
                                </Badge>
                              )}
                              {c.not_null && (
                                <span className="text-[10px] text-muted-foreground font-mono">
                                  NN
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <span
                                className={`font-mono text-[11px] ${
                                  c.null_percentage > 50
                                    ? "text-destructive font-bold"
                                    : c.null_percentage > 0
                                    ? "text-warning font-medium"
                                    : "text-muted-foreground"
                                }`}
                              >
                                {c.null_percentage}%
                              </span>
                              {c.null_percentage > 0 && (
                                <div className="w-12 bg-border rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className={`h-1.5 ${
                                      c.null_percentage > 50 ? "bg-destructive" : "bg-warning"
                                    }`}
                                    style={{ width: `${c.null_percentage}%` }}
                                  />
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="p-3 font-mono text-muted-foreground">
                            {c.distinct_count.toLocaleString()}
                          </td>
                          <td className="p-3 text-[11px] text-muted-foreground max-w-[200px] truncate">
                            {c.sample_values && c.sample_values.length > 0 ? (
                              <span className="text-foreground/90 font-mono">
                                [{c.sample_values.slice(0, 3).join(", ")}
                                {c.sample_values.length > 3 ? "..." : ""}]
                              </span>
                            ) : c.min_sample && c.max_sample ? (
                              <span className="font-mono text-foreground/80">
                                {c.min_sample} → {c.max_sample}
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Foreign Key Lineage Cards */}
                {selectedTable.foreign_keys.length > 0 && (
                  <div className="pt-4 border-t border-border/80 space-y-3">
                    <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                      <LinkIcon className="w-3.5 h-3.5 text-primary" />
                      <span>Foreign Key Lineage ({selectedTable.foreign_keys.length})</span>
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                      {selectedTable.foreign_keys.map((fk, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl bg-background/50 border border-border/80 flex items-center justify-between"
                        >
                          <span className="font-mono text-primary font-semibold">
                            {fk.source_column}
                          </span>
                          <ArrowRight className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                          <button
                            type="button"
                            onClick={() => setSelectedTableName(fk.target_table)}
                            className="font-mono text-foreground hover:text-primary transition-colors cursor-pointer text-left truncate"
                            title={`Jump to ${fk.target_table}`}
                          >
                            {fk.target_table}.{fk.target_column}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* 4. Sub-View B: Verified Business Metrics Glossary */}
      {activeSubTab === "metrics" && (
        <div className="space-y-4">
          <div className="p-5 rounded-2xl border border-border/80 bg-card/90 shadow-md">
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-warning" />
              <span>Verified Business Semantic Definitions</span>
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Standardized corporate metric definitions, calculation formulas, and filter conditions
            </p>
          </div>

          {isLoadingMetrics && (
            <div className="py-12 text-center text-xs text-muted-foreground">
              <RefreshCw className="w-5 h-5 animate-spin text-primary mx-auto mb-2" />
              <span>Loading business metrics from semantics registry...</span>
            </div>
          )}

          {!isLoadingMetrics && businessMetrics && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {businessMetrics.map((bm: BusinessMetric) => (
                <div
                  key={bm.name}
                  className="p-5 rounded-2xl border border-border/80 bg-card/80 space-y-3 shadow-sm hover:border-primary/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="font-semibold text-sm text-foreground">{bm.display_name}</h4>
                      <span className="font-mono text-[11px] text-primary">{bm.name}</span>
                    </div>
                    <Badge variant="mono" size="xs">
                      {bm.primary_tables.join(", ")}
                    </Badge>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {bm.plain_description}
                  </p>

                  <div className="space-y-1">
                    <span className="text-[10px] text-muted-foreground font-mono uppercase font-bold">
                      SQL Formula
                    </span>
                    <pre className="p-2.5 rounded-lg bg-background/80 text-[11px] font-mono text-primary border border-border/60 overflow-x-auto">
                      <code>{bm.formula_sql}</code>
                    </pre>
                  </div>

                  {bm.business_caveat && (
                    <p className="text-[11px] text-warning bg-warning/10 p-2 rounded-lg border border-warning/20">
                      <strong>Caveat:</strong> {bm.business_caveat}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

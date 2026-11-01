"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchSchemaStatus,
  fetchTableDetail,
  fetchTables,
  triggerSchemaPreparation,
} from "@/lib/api";
import { TableModel, TableSummary } from "@/types/api";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  Database,
  Hash,
  Key,
  Layers,
  Link,
  Play,
  RefreshCw,
  Search,
  Shield,
  Table,
} from "lucide-react";

export function SchemaReadinessSection() {
  const queryClient = useQueryClient();
  const [selectedTableName, setSelectedTableName] = useState<string | null>("orders");
  const [searchTerm, setSearchTerm] = useState("");

  // Query schema preparation status
  const { data: schemaStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["schemaStatus"],
    queryFn: fetchSchemaStatus,
    refetchInterval: (query) => {
      const state = query.state.data?.latest_job?.status;
      return state === "pending" || state === "running" ? 1500 : 15000;
    },
  });

  // Query tables list
  const { data: tables, isLoading: isLoadingTables, refetch: refetchTables } = useQuery({
    queryKey: ["schemaTables"],
    queryFn: fetchTables,
  });

  // Query selected table detail
  const { data: selectedTable, isLoading: isLoadingTableDetail } = useQuery({
    queryKey: ["tableDetail", selectedTableName],
    queryFn: () => (selectedTableName ? fetchTableDetail(selectedTableName) : null),
    enabled: !!selectedTableName,
  });

  // Prepare schema mutation
  const prepareMutation = useMutation({
    mutationFn: (force: boolean) => triggerSchemaPreparation(force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schemaStatus"] });
      queryClient.invalidateQueries({ queryKey: ["schemaTables"] });
    },
  });

  const isPreparing =
    prepareMutation.isPending ||
    schemaStatus?.latest_job?.status === "running" ||
    schemaStatus?.latest_job?.status === "pending";

  const filteredTables = (tables || []).filter((t) =>
    t.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <section className="space-y-6">
      {/* Schema Preparation Job Bar */}
      <div className="p-6 rounded-xl border border-border bg-card space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-primary" />
              <h2 className="text-base font-semibold text-foreground">
                Schema Catalogue & Preparation Engine
              </h2>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                  schemaStatus?.is_prepared
                    ? "bg-success/20 text-success border border-success/30"
                    : "bg-warning/20 text-warning border border-warning/30"
                }`}
              >
                {schemaStatus?.is_prepared ? "Catalogue Active" : "Unprepared"}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Idempotent profiling of tables, foreign-key lineage, null distributions, and candidate columns
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => prepareMutation.mutate(false)}
              disabled={isPreparing}
              className="px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center space-x-1.5 transition-colors"
            >
              {isPreparing ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              <span>{isPreparing ? "Profiling..." : "Run Preparation"}</span>
            </button>

            <button
              onClick={() => prepareMutation.mutate(true)}
              disabled={isPreparing}
              className="px-3 py-1.5 rounded-lg border border-border hover:bg-muted text-xs text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
              title="Force re-profiling bypasses cache"
            >
              Force Refresh
            </button>
          </div>
        </div>

        {/* Live Progress Bar if Job Running */}
        {isPreparing && (
          <div className="p-4 rounded-lg bg-background/60 border border-primary/30 space-y-2">
            <div className="flex justify-between text-xs">
              <span className="font-medium text-primary">
                {schemaStatus?.latest_job?.message || "Running preparation worker..."}
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

        {schemaStatus?.catalog_summary && !isPreparing && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2 border-t border-border">
            <div className="flex justify-between p-2 rounded bg-background/40">
              <span className="text-muted-foreground">Profiled Tables:</span>
              <span className="font-semibold text-foreground">
                {schemaStatus.catalog_summary.total_tables}
              </span>
            </div>
            <div className="flex justify-between p-2 rounded bg-background/40">
              <span className="text-muted-foreground">Total Records:</span>
              <span className="font-semibold text-foreground">
                {schemaStatus.catalog_summary.total_rows.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between p-2 rounded bg-background/40">
              <span className="text-muted-foreground">Fingerprint:</span>
              <span className="font-mono text-foreground truncate max-w-[90px]" title={schemaStatus.catalog_summary.source_fingerprint || ""}>
                {schemaStatus.catalog_summary.source_fingerprint?.slice(0, 10)}...
              </span>
            </div>
            <div className="flex justify-between p-2 rounded bg-background/40">
              <span className="text-muted-foreground">Status:</span>
              <span className="text-success font-medium">Cached & Ready</span>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Schema & Table Explorer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Table Selector (Left Pane) */}
        <div className="lg:col-span-4 p-4 rounded-xl border border-border bg-card space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center space-x-2 text-sm font-semibold text-foreground">
              <Table className="w-4 h-4 text-primary" />
              <span>Cataloged Tables</span>
            </div>
            <span className="text-xs font-mono text-muted-foreground">
              {filteredTables.length} / {tables?.length || 0}
            </span>
          </div>

          {/* Search box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter tables..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-background border border-border rounded-lg text-foreground focus:outline-none focus:border-primary"
            />
          </div>

          {/* Table List */}
          <div className="space-y-1 max-h-[500px] overflow-y-auto pr-1">
            {isLoadingTables && (
              <div className="p-4 text-center text-xs text-muted-foreground">Loading tables...</div>
            )}
            {filteredTables.map((tbl) => {
              const isSelected = selectedTableName === tbl.name;
              return (
                <button
                  key={tbl.name}
                  onClick={() => setSelectedTableName(tbl.name)}
                  className={`w-full text-left p-2.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                    isSelected
                      ? "bg-primary text-white font-medium"
                      : "hover:bg-muted text-foreground/90 border border-transparent"
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate">
                    <Table className={`w-3.5 h-3.5 flex-shrink-0 ${isSelected ? "text-white" : "text-primary"}`} />
                    <span className="truncate">{tbl.name}</span>
                  </div>
                  <div className="flex items-center space-x-2 flex-shrink-0 font-mono text-[11px]">
                    <span className={isSelected ? "text-white/80" : "text-muted-foreground"}>
                      {tbl.row_count.toLocaleString()} rows
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Table Profile Inspector (Right Pane) */}
        <div className="lg:col-span-8 p-6 rounded-xl border border-border bg-card space-y-4">
          {isLoadingTableDetail && (
            <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center space-y-2">
              <RefreshCw className="w-6 h-6 animate-spin text-primary" />
              <span>Loading schema profile...</span>
            </div>
          )}

          {!isLoadingTableDetail && selectedTable && (
            <>
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-border gap-2">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-lg font-bold text-foreground font-mono">
                      {selectedTable.name}
                    </h3>
                    <span className="text-xs px-2 py-0.5 rounded bg-primary/20 text-primary font-mono">
                      {selectedTable.row_count.toLocaleString()} rows
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                      {selectedTable.columns.length} columns
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Primary Key: {selectedTable.primary_key_columns.join(", ") || "RowID"} | Foreign Keys: {selectedTable.foreign_keys.length} | Indexes: {selectedTable.indexes.length}
                  </p>
                </div>
              </div>

              {/* Columns Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground font-medium">
                      <th className="pb-2">Column</th>
                      <th className="pb-2">Type</th>
                      <th className="pb-2">Constraints</th>
                      <th className="pb-2">Null Rate</th>
                      <th className="pb-2">Distinct</th>
                      <th className="pb-2">Sample / Range</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {selectedTable.columns.map((c) => (
                      <tr key={c.name} className="hover:bg-muted/40 transition-colors">
                        <td className="py-2.5 font-mono text-foreground font-medium">
                          {c.name}
                        </td>
                        <td className="py-2.5 font-mono text-muted-foreground">
                          {c.sqlite_type}
                        </td>
                        <td className="py-2.5">
                          <div className="flex items-center space-x-1.5 flex-wrap gap-1">
                            {c.is_pk && (
                              <span className="px-1.5 py-0.5 text-[10px] rounded bg-warning/20 text-warning font-semibold flex items-center space-x-0.5">
                                <Key className="w-2.5 h-2.5" />
                                <span>PK</span>
                              </span>
                            )}
                            {c.is_fk && (
                              <span
                                className="px-1.5 py-0.5 text-[10px] rounded bg-primary/20 text-primary flex items-center space-x-0.5"
                                title={`-> ${c.fk_target_table}.${c.fk_target_column}`}
                              >
                                <Link className="w-2.5 h-2.5" />
                                <span>FK</span>
                              </span>
                            )}
                            {c.is_date_candidate && (
                              <span className="px-1.5 py-0.5 text-[10px] rounded bg-muted text-foreground/80 flex items-center space-x-0.5">
                                <Calendar className="w-2.5 h-2.5" />
                                <span>Date</span>
                              </span>
                            )}
                            {c.is_numeric_candidate && !c.is_pk && !c.is_fk && (
                              <span className="px-1.5 py-0.5 text-[10px] rounded bg-muted text-foreground/80 flex items-center space-x-0.5">
                                <Hash className="w-2.5 h-2.5" />
                                <span>Num</span>
                              </span>
                            )}
                            {c.not_null && (
                              <span className="text-[10px] text-muted-foreground">NN</span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5">
                          <span
                            className={
                              c.null_percentage > 50
                                ? "text-destructive font-medium"
                                : c.null_percentage > 0
                                ? "text-warning"
                                : "text-muted-foreground"
                            }
                          >
                            {c.null_percentage}%
                          </span>
                        </td>
                        <td className="py-2.5 font-mono text-muted-foreground">
                          {c.distinct_count.toLocaleString()}
                        </td>
                        <td className="py-2.5 text-[11px] text-muted-foreground max-w-[200px] truncate">
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

              {/* Foreign Keys List if present */}
              {selectedTable.foreign_keys.length > 0 && (
                <div className="pt-4 border-t border-border space-y-2">
                  <h4 className="text-xs font-semibold text-foreground flex items-center space-x-1.5">
                    <Link className="w-3.5 h-3.5 text-primary" />
                    <span>Foreign Key Lineage ({selectedTable.foreign_keys.length})</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {selectedTable.foreign_keys.map((fk, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-background/50 border border-border flex items-center justify-between"
                      >
                        <span className="font-mono text-primary font-medium">{fk.source_column}</span>
                        <ArrowRight className="w-3 h-3 text-muted-foreground" />
                        <span className="font-mono text-foreground">
                          {fk.target_table}.{fk.target_column}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}


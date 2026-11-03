"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchLLMStatus,
  fetchDatabaseStatus,
  fetchSavedDatabases,
  activateSavedDatabase,
  disconnectDatabase,
  disconnectGroqLLM,
} from "@/lib/api";
import { GroqConnectionForm } from "./GroqConnectionForm";
import { DatabaseConnectionForm } from "./DatabaseConnectionForm";
import {
  Sparkles,
  Database,
  Server,
  HardDrive,
  Layers,
  CheckCircle2,
  Plus,
  RefreshCw,
  Power,
  Edit2,
  ShieldCheck,
  Radio,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

interface ConnectionManagerProps {
  onNavigateToPreparation?: (jobId: string) => void;
}

export function ConnectionManager({
  onNavigateToPreparation,
}: ConnectionManagerProps) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"connections" | "add_db" | "edit_llm">("connections");

  // Fetch LLM Status
  const { data: llmStatus, isLoading: loadingLLM } = useQuery({
    queryKey: ["llmStatus"],
    queryFn: fetchLLMStatus,
  });

  // Fetch Database Status
  const { data: dbStatus, isLoading: loadingDB } = useQuery({
    queryKey: ["dbStatus"],
    queryFn: fetchDatabaseStatus,
  });

  // Fetch Saved Databases
  const { data: savedDBs, isLoading: loadingSaved } = useQuery({
    queryKey: ["savedDatabases"],
    queryFn: fetchSavedDatabases,
  });

  // Activate Database Mutation
  const activateMutation = useMutation({
    mutationFn: async (id: string) => {
      return await activateSavedDatabase(id);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["dbStatus"] });
      queryClient.invalidateQueries({ queryKey: ["savedDatabases"] });
      queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
      queryClient.invalidateQueries({ queryKey: ["schemaStatus"] });
      queryClient.invalidateQueries({ queryKey: ["readiness"] });
      if (onNavigateToPreparation && data.preparation_job?.job_id) {
        onNavigateToPreparation(data.preparation_job.job_id);
      }
    },
  });

  // Disconnect DB Mutation
  const disconnectDBMutation = useMutation({
    mutationFn: disconnectDatabase,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dbStatus"] });
      queryClient.invalidateQueries({ queryKey: ["savedDatabases"] });
      queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
      queryClient.invalidateQueries({ queryKey: ["schemaStatus"] });
      queryClient.invalidateQueries({ queryKey: ["readiness"] });
    },
  });

  // Disconnect LLM Mutation
  const disconnectLLMMutation = useMutation({
    mutationFn: disconnectGroqLLM,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llmStatus"] });
      queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
      queryClient.invalidateQueries({ queryKey: ["readiness"] });
    },
  });

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Tab Navigation */}
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Connection Settings & Data Sources
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage your single-provider Groq LLM inference credentials and business database connections.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeTab !== "connections" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveTab("connections")}
            >
              ← Back to Connections
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setActiveTab("add_db")}
              icon={<Plus className="w-3.5 h-3.5" />}
            >
              Connect New Database
            </Button>
          )}
        </div>
      </div>

      {/* Main View: Active Connections */}
      {activeTab === "connections" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* LLM Card */}
          <div className="bg-card border border-border rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-foreground">AI Model Provider</h3>
                  <p className="text-xs text-muted-foreground">Groq Cloud API</p>
                </div>
              </div>

              <Badge
                variant={llmStatus?.connected ? "success" : "destructive"}
                size="xs"
              >
                {llmStatus?.connected ? "CONNECTED" : "NOT CONNECTED"}
              </Badge>
            </div>

            <div className="space-y-2.5 bg-background/60 p-3.5 rounded-xl border border-border/60 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-muted-foreground">ACTIVE MODEL</span>
                <span className="text-foreground font-semibold">{llmStatus?.model || "None"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">API KEY</span>
                <span className="text-foreground">{llmStatus?.masked_key || "None configured"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">INFERENCE ENGINE</span>
                <span className="text-foreground">Groq LPU (Ultra-Low Latency)</span>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActiveTab("edit_llm")}
                className="flex-1 justify-center"
                icon={<Edit2 className="w-3.5 h-3.5" />}
              >
                Change Key / Model
              </Button>
              {llmStatus?.connected && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => disconnectLLMMutation.mutate()}
                  isLoading={disconnectLLMMutation.isPending}
                  className="text-muted-foreground hover:text-destructive hover:border-destructive/40"
                  icon={<Power className="w-3.5 h-3.5" />}
                >
                  Disconnect
                </Button>
              )}
            </div>
          </div>

          {/* Active Database Card */}
          <div className="bg-card border border-border rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-foreground">Active Database</h3>
                  <p className="text-xs text-muted-foreground">
                    {dbStatus?.engine ? dbStatus.engine.toUpperCase() : "None"} (Read-Only)
                  </p>
                </div>
              </div>

              <Badge
                variant={dbStatus?.connected ? "success" : "destructive"}
                size="xs"
              >
                {dbStatus?.connected ? "CONNECTED" : "DISCONNECTED"}
              </Badge>
            </div>

            <div className="space-y-2.5 bg-background/60 p-3.5 rounded-xl border border-border/60 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-muted-foreground">DATABASE NAME</span>
                <span className="text-foreground font-semibold">{dbStatus?.name || "None"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">TABLES DISCOVERED</span>
                <span className="text-foreground">{dbStatus?.table_count || 0} tables</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">FINGERPRINT</span>
                <span className="text-foreground truncate max-w-[160px]">
                  {dbStatus?.fingerprint ? `${dbStatus.fingerprint.slice(0, 12)}...` : "--"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActiveTab("add_db")}
                className="flex-1 justify-center"
                icon={<Plus className="w-3.5 h-3.5" />}
              >
                Switch / Connect DB
              </Button>
              {dbStatus?.connected && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => disconnectDBMutation.mutate()}
                  isLoading={disconnectDBMutation.isPending}
                  className="text-muted-foreground hover:text-destructive hover:border-destructive/40"
                  icon={<Power className="w-3.5 h-3.5" />}
                >
                  Disconnect
                </Button>
              )}
            </div>
          </div>

          {/* Saved Databases List */}
          <div className="md:col-span-2 bg-card border border-border rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-sm text-foreground">Saved Database Connections</h3>
                <p className="text-xs text-muted-foreground">
                  The application maintains exactly one active database connection at a time. Switching invalidates fingerprint-dependent caches.
                </p>
              </div>
              <Badge variant="mono" size="xs">
                {savedDBs?.length || 0} Saved
              </Badge>
            </div>

            {loadingSaved ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2" />
                Loading saved databases...
              </div>
            ) : savedDBs && savedDBs.length > 0 ? (
              <div className="divide-y divide-border/60 border border-border/60 rounded-xl overflow-hidden">
                {savedDBs.map((db) => {
                  const isActive = db.is_active;
                  return (
                    <div
                      key={db.id}
                      className={`p-3.5 flex items-center justify-between text-xs transition-colors ${
                        isActive ? "bg-primary/5" : "bg-background/40 hover:bg-background/80"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                            isActive
                              ? "bg-primary text-white"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {db.engine === "sqlite" ? (
                            <HardDrive className="w-4 h-4" />
                          ) : db.engine === "postgresql" ? (
                            <Server className="w-4 h-4" />
                          ) : (
                            <Layers className="w-4 h-4" />
                          )}
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-foreground">{db.name}</span>
                            <Badge variant="mono" size="xs" className="uppercase text-[10px]">
                              {db.engine}
                            </Badge>
                            {isActive && (
                              <Badge variant="success" size="xs" className="gap-1">
                                <Radio className="w-2.5 h-2.5 animate-pulse" />
                                Active
                              </Badge>
                            )}
                          </div>
                          {db.fingerprint && (
                            <span className="text-[10px] font-mono text-muted-foreground">
                              Fingerprint: {db.fingerprint.slice(0, 16)}...
                            </span>
                          )}
                        </div>
                      </div>

                      <div>
                        {!isActive ? (
                          <Button
                            variant="outline"
                            size="xs"
                            onClick={() => activateMutation.mutate(db.id)}
                            isLoading={activateMutation.isPending}
                          >
                            Activate & Prepare
                          </Button>
                        ) : (
                          <Badge variant="outline" size="xs" className="text-success border-success/30">
                            Current Active
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-muted-foreground bg-background/40 rounded-xl border border-dashed border-border">
                No external databases saved yet. Connect a database to add it here.
              </div>
            )}
          </div>
        </div>
      )}

      {/* View: Add New Database */}
      {activeTab === "add_db" && (
        <DatabaseConnectionForm
          onSuccess={() => setActiveTab("connections")}
          onNavigateToPreparation={onNavigateToPreparation}
        />
      )}

      {/* View: Edit Groq LLM */}
      {activeTab === "edit_llm" && (
        <GroqConnectionForm
          showContinueButton={false}
          onSuccess={() => setActiveTab("connections")}
        />
      )}
    </div>
  );
}


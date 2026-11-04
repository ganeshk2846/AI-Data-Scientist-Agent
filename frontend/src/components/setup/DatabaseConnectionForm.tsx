"use client";

import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  testDatabaseConnection,
  uploadSQLiteFile,
  connectDatabase,
} from "@/lib/api";
import { PreparationJobState } from "@/types/api";
import {
  Database,
  Upload,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Server,
  Layers,
  ArrowRight,
  HardDrive,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { messageFrom } from "@/lib/errors";

type SupportedEngine = "sqlite" | "postgresql" | "mysql";

interface DatabaseConnectionFormProps {
  onSuccess?: (job: PreparationJobState) => void;
  onNavigateToPreparation?: (jobId: string) => void;
}

export function DatabaseConnectionForm({
  onSuccess,
  onNavigateToPreparation,
}: DatabaseConnectionFormProps) {
  const queryClient = useQueryClient();
  const [selectedEngine, setSelectedEngine] = useState<SupportedEngine>("sqlite");
  const [connectionName, setConnectionName] = useState("Enterprise Warehouse");

  // SQLite fields
  const [sqliteMode, setSqliteMode] = useState<"managed" | "upload">("managed");
  const [sqliteFilePath, setSqliteFilePath] = useState("ecommerce.db");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // PostgreSQL / MySQL fields
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState<number>(5432);
  const [databaseName, setDatabaseName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [ssl, setSsl] = useState(false);

  // Test status state
  const [testResult, setTestResult] = useState<{
    success: boolean;
    table_count?: number;
    message: string;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Update default port when switching engine
  const handleEngineChange = (engine: SupportedEngine) => {
    setSelectedEngine(engine);
    setTestResult(null);
    setErrorMessage(null);
    if (engine === "postgresql") {
      setPort(5432);
      if (connectionName === "Enterprise Warehouse" || connectionName === "MySQL Analytics") {
        setConnectionName("PostgreSQL Warehouse");
      }
    } else if (engine === "mysql") {
      setPort(3306);
      if (connectionName === "Enterprise Warehouse" || connectionName === "PostgreSQL Warehouse") {
        setConnectionName("MySQL Analytics");
      }
    } else {
      setConnectionName("Enterprise Warehouse");
    }
  };

  // Test Connection Mutation
  const testMutation = useMutation({
    mutationFn: async () => {
      setTestResult(null);
      setErrorMessage(null);

      let targetPath = sqliteFilePath;
      if (selectedEngine === "sqlite" && sqliteMode === "upload" && uploadedFile) {
        setIsUploading(true);
        const uploadRes = await uploadSQLiteFile(uploadedFile);
        targetPath = uploadRes.file_path;
        setSqliteFilePath(uploadRes.file_path);
        setIsUploading(false);
      }

      return await testDatabaseConnection({
        engine: selectedEngine,
        name: connectionName,
        file_path: selectedEngine === "sqlite" ? targetPath : undefined,
        host: selectedEngine !== "sqlite" ? host : undefined,
        port: selectedEngine !== "sqlite" ? Number(port) : undefined,
        database: selectedEngine !== "sqlite" ? databaseName : undefined,
        username: selectedEngine !== "sqlite" ? username : undefined,
        password: selectedEngine !== "sqlite" ? password : undefined,
        ssl: ssl,
      });
    },
    onSuccess: (data) => {
      setTestResult({
        success: true,
        table_count: data.table_count,
        message: data.message || `Discovered ${data.table_count} tables. Connection verified.`,
      });
    },
    onError: (err: unknown) => {
      setIsUploading(false);
      setErrorMessage(messageFrom(err, "Database connection test failed."));
    },
  });

  // Connect Database Mutation
  const connectMutation = useMutation({
    mutationFn: async () => {
      setErrorMessage(null);

      let targetPath = sqliteFilePath;
      if (selectedEngine === "sqlite" && sqliteMode === "upload" && uploadedFile) {
        setIsUploading(true);
        const uploadRes = await uploadSQLiteFile(uploadedFile);
        targetPath = uploadRes.file_path;
        setIsUploading(false);
      }

      return await connectDatabase({
        engine: selectedEngine,
        name: connectionName,
        file_path: selectedEngine === "sqlite" ? targetPath : undefined,
        host: selectedEngine !== "sqlite" ? host : undefined,
        port: selectedEngine !== "sqlite" ? Number(port) : undefined,
        database: selectedEngine !== "sqlite" ? databaseName : undefined,
        username: selectedEngine !== "sqlite" ? username : undefined,
        password: selectedEngine !== "sqlite" ? password : undefined,
        ssl: ssl,
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["dbStatus"] });
      queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
      queryClient.invalidateQueries({ queryKey: ["schemaStatus"] });
      queryClient.invalidateQueries({ queryKey: ["readiness"] });

      const job = data.preparation_job;
      if (onSuccess) {
        onSuccess(job);
      }
      if (onNavigateToPreparation && job?.job_id) {
        onNavigateToPreparation(job.job_id);
      }
    },
    onError: (err: unknown) => {
      setIsUploading(false);
      setErrorMessage(messageFrom(err, "Failed to establish database connection."));
    },
  });

  return (
    <div className="bg-surface border border-[var(--border)] rounded-card p-6 sm:p-8 max-w-xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div>
          <h2 className="text-title font-semibold tracking-tight text-text flex items-center gap-2">
            Connect Your Business Database
            <Badge variant="success" size="xs" className="font-mono">
              mode=ro
            </Badge>
          </h2>
          <p className="text-label text-muted mt-1">
            Connect the database containing the business information you want to analyze. Strict read-only access is enforced on all queries.
          </p>
        </div>
      </div>

      {/* Engine Tabs */}
      <div className="space-y-2">
        <label className="text-label font-semibold text-muted">
          Database Engine
        </label>
        <div className="grid grid-cols-3 gap-2 p-1 bg-ground rounded-card border border-[var(--border)]">
          <button
            type="button"
            onClick={() => handleEngineChange("sqlite")}
            className={`py-2 px-3 rounded-control text-label font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer ${
              selectedEngine === "sqlite"
                ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                : "text-muted hover:text-text"
            }`}
          >
            <HardDrive className="w-3.5 h-3.5" />
            <span>SQLite</span>
          </button>
          <button
            type="button"
            onClick={() => handleEngineChange("postgresql")}
            className={`py-2 px-3 rounded-control text-label font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer ${
              selectedEngine === "postgresql"
                ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                : "text-muted hover:text-text"
            }`}
          >
            <Server className="w-3.5 h-3.5" />
            <span>PostgreSQL</span>
          </button>
          <button
            type="button"
            onClick={() => handleEngineChange("mysql")}
            className={`py-2 px-3 rounded-control text-label font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer ${
              selectedEngine === "mysql"
                ? "bg-[var(--primary)] text-[var(--primary-ink)]"
                : "text-muted hover:text-text"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>MySQL</span>
          </button>
        </div>
      </div>

      {/* Connection Name */}
      <div className="space-y-1.5">
        <label className="text-label font-semibold text-muted">
          Connection Name
        </label>
        <input
          type="text"
          value={connectionName}
          onChange={(e) => setConnectionName(e.target.value)}
          placeholder="e.g. Production Analytics"
          required
          className="w-full bg-ground border border-[var(--border)] rounded-card px-3.5 py-2.5 text-body text-text focus:outline-none focus:ring-2 focus:ring-[var(--control)]"
        />
      </div>

      {/* SQLite Specific Controls */}
      {selectedEngine === "sqlite" && (
        <div className="space-y-4 pt-1">
          <div className="flex gap-2 text-label">
            <button
              type="button"
              onClick={() => setSqliteMode("managed")}
              className={`flex-1 py-1.5 px-3 rounded-control border text-center transition-colors cursor-pointer ${
                sqliteMode === "managed"
                  ? "bg-raised border-primary text-text font-medium"
                  : "bg-ground border-[var(--border)] text-muted"
              }`}
            >
              Default Business DB (ecommerce.db)
            </button>
            <button
              type="button"
              onClick={() => setSqliteMode("upload")}
              className={`flex-1 py-1.5 px-3 rounded-control border text-center transition-colors cursor-pointer ${
                sqliteMode === "upload"
                  ? "bg-raised border-primary text-text font-medium"
                  : "bg-ground border-[var(--border)] text-muted"
              }`}
            >
              Upload SQLite File
            </button>
          </div>

          {sqliteMode === "managed" ? (
            <div className="p-3.5 rounded-card bg-ground border border-[var(--border)] space-y-1.5 text-label">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-text">ecommerce.db</span>
                <Badge variant="mono" size="xs">
                  46 Tables
                </Badge>
              </div>
              <p className="text-muted text-micro">
                Pre-configured e-commerce schema with 2.4M rows across orders, customers, products, inventory, payments, marketing and telemetry.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="text-label font-semibold text-muted">
                Upload SQLite Database (.db, .sqlite)
              </label>
              <div className="border-2 border-dashed border-[var(--border)] rounded-card p-5 text-center bg-ground hover:bg-ground transition-colors">
                <input
                  type="file"
                  id="sqlite-file-input"
                  accept=".db,.sqlite,.sqlite3"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setUploadedFile(file);
                    setTestResult(null);
                  }}
                  className="hidden"
                />
                <label
                  htmlFor="sqlite-file-input"
                  className="cursor-pointer flex flex-col items-center gap-2"
                >
                  <Upload className="w-6 h-6 text-muted" />
                  <span className="text-label font-medium text-text">
                    {uploadedFile ? uploadedFile.name : "Click to select SQLite file"}
                  </span>
                  <span className="text-micro text-muted">
                    Supports .db, .sqlite formats (Validated by SQLite format 3 magic header)
                  </span>
                </label>
              </div>
            </div>
          )}
        </div>
      )}

      {/* PostgreSQL & MySQL Form Fields */}
      {(selectedEngine === "postgresql" || selectedEngine === "mysql") && (
        <div className="space-y-3.5 pt-1">
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 space-y-1.5">
              <label className="text-label font-semibold text-muted">
                Host
              </label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="localhost or db.company.com"
                required
                className="w-full bg-ground border border-[var(--border)] rounded-card px-3.5 py-2 text-body text-text focus:outline-none focus:ring-2 focus:ring-[var(--control)]"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-label font-semibold text-muted">
                Port
              </label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(Number(e.target.value))}
                required
                className="w-full bg-ground border border-[var(--border)] rounded-card px-3.5 py-2 text-body text-text focus:outline-none focus:ring-2 focus:ring-[var(--control)] font-mono"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-label font-semibold text-muted">
              Database Name
            </label>
            <input
              type="text"
              value={databaseName}
              onChange={(e) => setDatabaseName(e.target.value)}
              placeholder="e.g. analytics_warehouse"
              required
              className="w-full bg-ground border border-[var(--border)] rounded-card px-3.5 py-2 text-body text-text focus:outline-none focus:ring-2 focus:ring-[var(--control)]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-label font-semibold text-muted">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="readonly_user"
                required
                className="w-full bg-ground border border-[var(--border)] rounded-card px-3.5 py-2 text-body text-text focus:outline-none focus:ring-2 focus:ring-[var(--control)]"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-label font-semibold text-muted">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-ground border border-[var(--border)] rounded-card px-3.5 py-2 text-body text-text focus:outline-none focus:ring-2 focus:ring-[var(--control)]"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="ssl-checkbox"
              checked={ssl}
              onChange={(e) => setSsl(e.target.checked)}
              className="w-4 h-4 rounded text-text focus:ring-primary cursor-pointer"
            />
            <label htmlFor="ssl-checkbox" className="text-label text-muted cursor-pointer">
              Enable SSL / TLS encryption
            </label>
          </div>
        </div>
      )}

      {/* Safety Notice */}
      <div className="flex items-center gap-2 p-3 rounded-card bg-pill-positive-bg border border-[var(--border)] text-label text-muted">
        <ShieldCheck className="w-4 h-4 text-positive shrink-0" />
        <span>Strict read-only access (mode=ro, PRAGMA query_only=ON). Credentials encrypted on backend.</span>
      </div>

      {/* Test Result Feedback */}
      {testResult && (
        <div className="p-3.5 rounded-card bg-pill-positive-bg border border-[var(--border)] flex items-start gap-2.5 text-positive text-label">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold block">Connection Successful</span>
            <span>{testResult.message}</span>
          </div>
        </div>
      )}

      {/* Error Message Feedback */}
      {errorMessage && (
        <div className="p-3.5 rounded-card bg-pill-negative-bg border border-[var(--border)] flex items-start gap-2.5 text-negative text-label">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold block">Connection Failed</span>
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-3 pt-2">
        <Button
          type="button"
          variant="outline"
          size="md"
          onClick={() => testMutation.mutate()}
          isLoading={testMutation.isPending || isUploading}
          className="flex-1 justify-center"
        >
          {testMutation.isPending ? "Testing..." : "Test Connection"}
        </Button>

        <Button
          type="button"
          variant="primary"
          size="md"
          onClick={() => connectMutation.mutate()}
          isLoading={connectMutation.isPending || isUploading}
          className="flex-1 justify-center"
          icon={<ArrowRight className="w-4 h-4" />}
        >
          {connectMutation.isPending ? "Connecting..." : "Connect Database"}
        </Button>
      </div>
    </div>
  );
}


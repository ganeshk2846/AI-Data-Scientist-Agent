import {
  MultiAgentWorkflowResponseSchema,
  MultiAgentWorkflowResult,
  PreparationJobResponseSchema,
  PreparationJobState,
  ReadinessResponseSchema,
  ReadinessStatus,
  SchemaStatus,
  SchemaStatusResponseSchema,
  TableDetailResponseSchema,
  TableListResponseSchema,
  TableModel,
  TableSummary,
  BusinessMetric,
  BusinessMetricsListResponseSchema,
  RetrievalDiagnosticPayload,
  RetrievalDiagnosticResponseSchema,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchReadiness(): Promise<ReadinessStatus> {
  const url = `${API_BASE_URL}/api/v1/ready`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = ReadinessResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch readiness status");
  }
  return parsed.data.data;
}

export async function fetchSchemaStatus(): Promise<SchemaStatus> {
  const url = `${API_BASE_URL}/api/v1/schema/status`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = SchemaStatusResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch schema status");
  }
  return parsed.data.data;
}

export async function triggerSchemaPreparation(force: boolean = false): Promise<PreparationJobState> {
  const url = `${API_BASE_URL}/api/v1/schema/prepare?force=${force}`;
  const res = await fetch(url, { method: "POST", headers: { Accept: "application/json" } });
  const json = await res.json();
  const parsed = PreparationJobResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to trigger schema preparation");
  }
  return parsed.data.data;
}

export async function fetchTables(): Promise<TableSummary[]> {
  const url = `${API_BASE_URL}/api/v1/schema/tables`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" } });
  const json = await res.json();
  const parsed = TableListResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch tables list");
  }
  return parsed.data.data;
}

export async function fetchTableDetail(tableName: string): Promise<TableModel> {
  const url = `${API_BASE_URL}/api/v1/schema/tables/${encodeURIComponent(tableName)}`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" } });
  const json = await res.json();
  const parsed = TableDetailResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || `Failed to fetch table profile for ${tableName}`);
  }
  return parsed.data.data;
}

export async function executeChatQuery(queryText: string): Promise<MultiAgentWorkflowResult> {
  const url = `${API_BASE_URL}/api/v1/chat/query`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query: queryText }),
  });
  const json = await res.json();
  const parsed = MultiAgentWorkflowResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to execute multi-agent business query");
  }
  return parsed.data.data;
}


export async function fetchBusinessMetrics(): Promise<BusinessMetric[]> {
  const url = `${API_BASE_URL}/api/v1/retrieval/metrics`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" } });
  const json = await res.json();
  const parsed = BusinessMetricsListResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch business metrics");
  }
  return parsed.data.data;
}

export async function searchRetrieval(query: string, topK: number = 5): Promise<RetrievalDiagnosticPayload> {
  const url = `${API_BASE_URL}/api/v1/retrieval/search`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
  const json = await res.json();
  const parsed = RetrievalDiagnosticResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to execute hybrid retrieval search");
  }
  return parsed.data.data;
}

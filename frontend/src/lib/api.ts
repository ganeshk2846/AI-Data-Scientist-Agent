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
  ObservabilityMetrics,
  ObservabilityMetricsResponseSchema,
  RunTraceRecord,
  RunTraceListResponseSchema,
  SessionModel,
  SessionListResponseSchema,
  TurnModel,
  SessionDetailResponseSchema,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

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

export async function executeChatQuery(queryText: string, sessionId?: string): Promise<MultiAgentWorkflowResult> {
  const url = `${API_BASE_URL}/api/v1/chat/query`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query: queryText, session_id: sessionId }),
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


export async function clearSessionApi(sessionId: string): Promise<boolean> {
  const url = `${API_BASE_URL}/api/v1/memory/sessions/${encodeURIComponent(sessionId)}/clear`;
  const res = await fetch(url, { method: "POST", headers: { Accept: "application/json" } });
  const json = await res.json();
  return Boolean(json.success);
}

export async function fetchObservabilityMetrics(): Promise<ObservabilityMetrics> {
  const url = `${API_BASE_URL}/api/v1/ops/metrics`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = ObservabilityMetricsResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch observability metrics");
  }
  return parsed.data.data;
}

export async function fetchRecentTraces(limit: number = 25): Promise<RunTraceRecord[]> {
  const url = `${API_BASE_URL}/api/v1/ops/traces?limit=${limit}`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = RunTraceListResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch run traces");
  }
  return parsed.data.data;
}

export async function fetchSessions(): Promise<SessionModel[]> {
  const url = `${API_BASE_URL}/api/v1/memory/sessions`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = SessionListResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch sessions");
  }
  return parsed.data.data;
}

export async function fetchSessionDetail(sessionId: string): Promise<{ session: SessionModel; turns: TurnModel[] }> {
  const url = `${API_BASE_URL}/api/v1/memory/sessions/${encodeURIComponent(sessionId)}`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = SessionDetailResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch session detail");
  }
  return parsed.data.data;
}

export async function streamChatQuery(
  queryText: string,
  sessionId: string,
  onProgress: (step: string, message: string) => void,
  onResult: (result: MultiAgentWorkflowResult) => void,
  onError: (error: string) => void
): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/chat/stream`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ query: queryText, session_id: sessionId }),
    });

    if (!res.ok) {
      const errText = await res.text();
      onError(`Stream request failed (${res.status}): ${errText}`);
      return;
    }

    if (!res.body) {
      onError("No response body available for streaming");
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Normalize CRLF from sse_starlette to LF so chunk boundaries split reliably
      const normalized = buffer.replace(/\r\n/g, "\n");
      const blocks = normalized.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        if (!block.trim()) continue;
        let eventType = "message";
        const dataLines: string[] = [];

        for (const line of block.split("\n")) {
          const trimmed = line.trim();
          if (trimmed.startsWith("event:")) {
            eventType = trimmed.slice(6).trim();
          } else if (trimmed.startsWith("data:")) {
            dataLines.push(trimmed.slice(5).trim());
          }
        }

        const dataStr = dataLines.join("\n");

        if (eventType === "progress" && dataStr) {
          try {
            const data = JSON.parse(dataStr);
            onProgress(data.step, data.message);
          } catch (e) {
            console.error("Failed to parse progress event:", e);
          }
        } else if (eventType === "result" && dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            onResult(parsed as MultiAgentWorkflowResult);
          } catch (e) {
            console.error("Failed to parse result event:", e);
            onError("Failed to parse workflow result data.");
          }
        } else if (eventType === "error" && dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            onError(parsed.error || "Execution error in stream");
          } catch {
            onError(dataStr);
          }
        }
      }
    }

    // Flush any remaining completed block in buffer
    if (buffer.trim()) {
      const normalized = buffer.replace(/\r\n/g, "\n");
      for (const block of normalized.split("\n\n")) {
        if (!block.trim()) continue;
        let eventType = "message";
        const dataLines: string[] = [];
        for (const line of block.split("\n")) {
          const trimmed = line.trim();
          if (trimmed.startsWith("event:")) {
            eventType = trimmed.slice(6).trim();
          } else if (trimmed.startsWith("data:")) {
            dataLines.push(trimmed.slice(5).trim());
          }
        }
        const dataStr = dataLines.join("\n");
        if (eventType === "result" && dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            onResult(parsed as MultiAgentWorkflowResult);
          } catch (e) {
            console.error("Failed to parse flushed result event:", e);
          }
        }
      }
    }
  } catch (err: any) {
    console.error("Stream connection error:", err);
    onError(err.message || "Failed to connect to stream");
  }
}

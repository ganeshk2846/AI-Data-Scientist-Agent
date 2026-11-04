import {
  MultiAgentWorkflowResponseSchema,
  MultiAgentWorkflowResultSchema,
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
  StageSpanRecord,
  SessionModel,
  SessionListResponseSchema,
  TurnModel,
  SessionDetailResponseSchema,
  SupervisorExecutionResult,
  SupervisorExecutionResponseSchema,
  LLMStatusData,
  LLMStatusResponseSchema,
  LLMModelInfo,
  LLMModelListResponseSchema,
  DatabaseStatusInfo,
  DatabaseStatusResponseSchema,
  SavedDatabaseInfo,
  SavedDatabaseListResponseSchema,
  SetupStatusResponse,
  SetupStatusAPIResponseSchema,
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

export async function fetchObservabilityMetrics(
  window: string = "all",
  orchestrator: string = "all",
  status: string = "all"
): Promise<ObservabilityMetrics> {
  const params = new URLSearchParams();
  if (window) params.append("window", window);
  if (orchestrator) params.append("orchestrator", orchestrator);
  if (status) params.append("status", status);
  const url = `${API_BASE_URL}/api/v1/ops/metrics?${params.toString()}`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = ObservabilityMetricsResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch observability metrics");
  }
  return parsed.data.data;
}

export async function fetchRunSpans(runId: string): Promise<StageSpanRecord[]> {
  const url = `${API_BASE_URL}/api/v1/ops/spans/${encodeURIComponent(runId)}`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  return json.data || [];
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

/**
 * Parses an SSE `result` payload through the workflow schema.
 *
 * The previous implementation cast the JSON straight to the result type, so a
 * backend field the schema did not declare was invisible and a malformed
 * payload failed later with no explanation. Validating here means a drift
 * between backend and contract is reported instead of silently dropped.
 */
function parseWorkflowResult(raw: unknown): MultiAgentWorkflowResult | null {
  const parsed = MultiAgentWorkflowResultSchema.safeParse(raw);
  if (parsed.success) return parsed.data;
  console.error("Workflow result failed contract validation:", parsed.error.issues.slice(0, 8));
  return null;
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
            const result = parseWorkflowResult(JSON.parse(dataStr));
            if (result) {
              onResult(result);
            } else {
              onError("The analysis result did not match the expected contract.");
            }
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
            const result = parseWorkflowResult(JSON.parse(dataStr));
            if (result) onResult(result);
          } catch (e) {
            console.error("Failed to parse flushed result event:", e);
          }
        }
      }
    }
  } catch (err: unknown) {
    console.error("Stream connection error:", err);
    onError(err instanceof Error ? err.message : "Failed to connect to stream");
  }
}


// =====================================================================
// Phase 4: Domain-Independent Analytics Client Functions
// =====================================================================

export async function classifyAnalyticsIntent(question: string) {
  const url = `${API_BASE_URL}/api/v1/analytics/classify`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ question }),
  });
  const json = await res.json();
  if (!json.success) {
    throw new Error(json.error?.message || "Failed to classify question");
  }
  return json.data;
}

export async function generateAnalyticsPlan(question: string, intentOverride?: string) {
  const url = `${API_BASE_URL}/api/v1/analytics/plan`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ question, intent_override: intentOverride }),
  });
  const json = await res.json();
  if (!json.success) {
    throw new Error(json.error?.message || "Failed to generate analytical plan");
  }
  return json.data;
}

export async function executeAnalytics(question: string, sessionId?: string) {
  const url = `${API_BASE_URL}/api/v1/analytics/execute`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  const json = await res.json();
  if (!json.success) {
    throw new Error(json.error?.message || "Failed to execute analysis");
  }
  return json.data;
}

export async function evaluateAnalyticsClassifier() {
  const url = `${API_BASE_URL}/api/v1/analytics/evaluate-classifier`;
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const json = await res.json();
  if (!json.success) {
    throw new Error(json.error?.message || "Failed to evaluate classifier");
  }
  return json.data;
}


// =====================================================================
// Phase 5: Agentic Supervisor & Multi-Agent Decision Support APIs
// =====================================================================

export async function superviseAnalysis(
  question: string,
  sessionId?: string,
  intentOverride?: string
): Promise<SupervisorExecutionResult> {
  const url = `${API_BASE_URL}/api/v1/agentic/supervise`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ question, session_id: sessionId, intent_override: intentOverride }),
  });
  const json = await res.json();
  const parsed = SupervisorExecutionResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to execute agentic supervision");
  }
  return parsed.data.data;
}

export async function streamAgenticQuery(
  question: string,
  sessionId?: string,
  intentOverride?: string,
  onTaskProgress?: (task: unknown) => void,
  onResult?: (result: unknown) => void,
  onError?: (errorMsg: string) => void
): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/agentic/stream`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ question, session_id: sessionId, intent_override: intentOverride }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`SSE stream connection failed with HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const block of lines) {
      if (!block.trim()) continue;
      let eventType = "message";
      let eventData = "";

      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.replace("event:", "").trim();
        } else if (line.startsWith("data:")) {
          eventData = line.replace("data:", "").trim();
        }
      }

      if (eventData) {
        try {
          const parsedData = JSON.parse(eventData);
          if (eventType === "task_progress" && onTaskProgress) {
            onTaskProgress(parsedData);
          } else if (eventType === "result" && onResult) {
            onResult(parsedData);
          } else if (eventType === "error" && onError) {
            onError(parsedData.message || "Execution error in stream");
          }
        } catch (e) {
          console.warn("Failed to parse SSE payload:", e);
        }
      }
    }
  }
}

// ==========================================
// Setup, LLM & Database Connection Client APIs
// ==========================================

export async function fetchSetupStatus(): Promise<SetupStatusResponse> {
  const url = `${API_BASE_URL}/api/v1/setup/status`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = SetupStatusAPIResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch setup readiness status");
  }
  return parsed.data.data;
}

export async function fetchLLMStatus(): Promise<LLMStatusData> {
  const url = `${API_BASE_URL}/api/v1/llm/status`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = LLMStatusResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch LLM status");
  }
  return parsed.data.data;
}

export async function fetchSupportedModels(): Promise<LLMModelInfo[]> {
  const url = `${API_BASE_URL}/api/v1/llm/models`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = LLMModelListResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch supported Groq models");
  }
  return parsed.data.data;
}

export async function connectGroqLLM(apiKey: string, model: string): Promise<LLMStatusData> {
  const url = `${API_BASE_URL}/api/v1/llm/connect`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ api_key: apiKey, model }),
  });
  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.detail || json.message || "Failed to connect to Groq API");
  }
  const parsed = LLMStatusResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Invalid response connecting to Groq");
  }
  return parsed.data.data;
}

export async function disconnectGroqLLM(): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/llm/disconnect`;
  const res = await fetch(url, { method: "POST", headers: { Accept: "application/json" } });
  if (!res.ok) {
    const json = await res.json();
    throw new Error(json.detail || "Failed to disconnect Groq LLM");
  }
}

export async function fetchDatabaseStatus(): Promise<DatabaseStatusInfo> {
  const url = `${API_BASE_URL}/api/v1/db/status`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = DatabaseStatusResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch active database status");
  }
  return parsed.data.data;
}

export async function fetchSavedDatabases(): Promise<SavedDatabaseInfo[]> {
  const url = `${API_BASE_URL}/api/v1/db/saved`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = SavedDatabaseListResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to fetch saved databases");
  }
  return parsed.data.data;
}

export async function testDatabaseConnection(params: {
  engine: string;
  name?: string;
  file_path?: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  ssl?: boolean;
}): Promise<{ engine: string; table_count: number; message: string }> {
  const url = `${API_BASE_URL}/api/v1/db/test`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(params),
  });
  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.detail || json.message || "Failed to verify database connection");
  }
  return json.data;
}

export async function uploadSQLiteFile(file: File): Promise<{ file_path: string; filename: string; size_bytes: number }> {
  const url = `${API_BASE_URL}/api/v1/db/upload-sqlite`;
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json" },
    body: formData,
  });
  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.detail || json.message || "Failed to upload SQLite file");
  }
  return json.data;
}

export async function connectDatabase(params: {
  engine: string;
  name: string;
  file_path?: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  ssl?: boolean;
}): Promise<{ database: DatabaseStatusInfo; preparation_job: PreparationJobState }> {
  const url = `${API_BASE_URL}/api/v1/db/connect`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(params),
  });
  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.detail || json.message || "Failed to connect database");
  }
  return json.data;
}

export async function activateSavedDatabase(databaseId: string): Promise<{ database: DatabaseStatusInfo; preparation_job: PreparationJobState }> {
  const url = `${API_BASE_URL}/api/v1/db/activate/${encodeURIComponent(databaseId)}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.detail || json.message || "Failed to activate saved database");
  }
  return json.data;
}

export async function disconnectDatabase(): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/db/disconnect`;
  const res = await fetch(url, { method: "POST", headers: { Accept: "application/json" } });
  if (!res.ok) {
    const json = await res.json();
    throw new Error(json.detail || "Failed to disconnect database");
  }
}

export async function fetchPreparationJob(jobId: string): Promise<PreparationJobState> {
  const url = `${API_BASE_URL}/api/v1/schema/jobs/${encodeURIComponent(jobId)}`;
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" });
  const json = await res.json();
  const parsed = PreparationJobResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || `Failed to fetch preparation job ${jobId}`);
  }
  return parsed.data.data;
}

export async function retryPreparationJob(): Promise<PreparationJobState> {
  const url = `${API_BASE_URL}/api/v1/setup/retry-preparation`;
  const res = await fetch(url, { method: "POST", headers: { Accept: "application/json" } });
  const json = await res.json();
  const parsed = PreparationJobResponseSchema.safeParse(json);
  if (!parsed.success || !parsed.data.data) {
    throw new Error(parsed.data?.error?.message || "Failed to retry preparation job");
  }
  return parsed.data.data;
}


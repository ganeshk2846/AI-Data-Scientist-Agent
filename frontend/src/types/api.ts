import { z } from "zod";

export const ErrorDetailSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.any()).nullable().optional(),
  timestamp: z.string().optional(),
});

export const HealthStatusSchema = z.object({
  status: z.string(),
  version: z.string(),
  environment: z.string(),
  timestamp: z.string(),
});

export const DatabaseReadinessSchema = z.object({
  connected: z.boolean(),
  read_only_verified: z.boolean(),
  path: z.string(),
  size_bytes: z.number().nullable().optional(),
  table_count: z.number().nullable().optional(),
  total_rows: z.number().nullable().optional(),
  error: z.string().nullable().optional(),
});

export const LLMReadinessSchema = z.object({
  provider: z.string(),
  configured: z.boolean(),
  model: z.string(),
  message: z.string(),
});

export const ReadinessStatusSchema = z.object({
  ready: z.boolean(),
  database: DatabaseReadinessSchema,
  llm: LLMReadinessSchema,
  app_store_ready: z.boolean(),
  version: z.string(),
  timestamp: z.string(),
});

// Phase 2 Schema Models
export const ColumnModelSchema = z.object({
  name: z.string(),
  sqlite_type: z.string(),
  is_pk: z.boolean(),
  not_null: z.boolean(),
  default_value: z.string().nullable().optional(),
  is_fk: z.boolean(),
  fk_target_table: z.string().nullable().optional(),
  fk_target_column: z.string().nullable().optional(),
  is_date_candidate: z.boolean(),
  is_numeric_candidate: z.boolean(),
  null_count: z.number(),
  null_percentage: z.number(),
  distinct_count: z.number(),
  min_sample: z.string().nullable().optional(),
  max_sample: z.string().nullable().optional(),
  sample_values: z.array(z.string()).default([]),
});

export const ForeignKeyModelSchema = z.object({
  source_column: z.string(),
  target_table: z.string(),
  target_column: z.string(),
  on_update: z.string().nullable().optional(),
  on_delete: z.string().nullable().optional(),
});

export const IndexModelSchema = z.object({
  name: z.string(),
  unique: z.boolean(),
  columns: z.array(z.string()),
});

export const TableModelSchema = z.object({
  name: z.string(),
  row_count: z.number(),
  columns: z.array(ColumnModelSchema),
  foreign_keys: z.array(ForeignKeyModelSchema),
  indexes: z.array(IndexModelSchema),
  primary_key_columns: z.array(z.string()),
  description: z.string().nullable().optional(),
});

export const TableSummarySchema = z.object({
  name: z.string(),
  row_count: z.number(),
  column_count: z.number(),
  primary_keys: z.array(z.string()),
  foreign_key_count: z.number(),
  index_count: z.number(),
});

export const DatabaseCatalogSchema = z.object({
  source_fingerprint: z.string(),
  database_path: z.string(),
  generated_at: z.string(),
  total_tables: z.number(),
  total_rows: z.number(),
  tables: z.record(TableModelSchema),
  foreign_key_graph: z.array(z.record(z.string())),
});

export const PreparationJobStateSchema = z.object({
  job_id: z.string(),
  status: z.enum(["pending", "running", "succeeded", "failed"]),
  progress_percent: z.number(),
  current_table: z.string().nullable().optional(),
  message: z.string(),
  started_at: z.string(),
  completed_at: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
  tables_processed: z.number().default(0),
  total_tables: z.number().default(0),
  source_fingerprint: z.string().nullable().optional(),
});

export const SchemaStatusSchema = z.object({
  is_prepared: z.boolean(),
  latest_job: PreparationJobStateSchema.nullable().optional(),
  catalog_summary: z
    .object({
      total_tables: z.number(),
      total_rows: z.number(),
      generated_at: z.string().nullable().optional(),
      source_fingerprint: z.string().nullable().optional(),
    })
    .nullable()
    .optional(),
});

// Phase 3 Chat & Workflow Models
export const RouteResultSchema = z.object({
  intent: z.enum(["descriptive", "comparative", "trend", "diagnostic", "predictive", "prescriptive"]),
  confidence: z.number(),
  complexity: z.enum(["simple", "medium", "complex"]),
  reasoning: z.string(),
  target_domains: z.array(z.string()).default([]),
  suggested_entities: z.array(z.string()).default([]),
});

export const StepTraceSchema = z.object({
  step: z.string(),
  status: z.enum(["running", "succeeded", "failed", "skipped"]),
  duration_ms: z.number(),
  message: z.string(),
  metadata: z.record(z.any()).nullable().optional(),
});

export const QueryExecutionResultSchema = z.object({
  sql: z.string(),
  columns: z.array(z.string()),
  rows: z.array(z.record(z.any())),
  row_count: z.number(),
  execution_time_ms: z.number(),
  truncated: z.boolean().default(false),
  error: z.string().nullable().optional(),
});

export const VerificationResultSchema = z.object({
  is_valid: z.boolean(),
  empty_result: z.boolean().default(false),
  row_count: z.number(),
  checks_passed: z.array(z.string()).default([]),
  warnings: z.array(z.string()).default([]),
});

export const QueryWorkflowResultSchema = z.object({
  run_id: z.string(),
  query: z.string(),
  route: RouteResultSchema,
  selected_tables: z.array(z.string()),
  generated_sql: z.string().nullable().optional(),
  sanitized_sql: z.string().nullable().optional(),
  query_result: QueryExecutionResultSchema.nullable().optional(),
  verification: VerificationResultSchema.nullable().optional(),
  composed_answer: z.string(),
  key_findings: z.array(z.string()).default([]),
  limitations: z.array(z.string()).default([]),
  trace_steps: z.array(StepTraceSchema).default([]),
  total_duration_ms: z.number(),
  timestamp: z.string(),
});

export function createAPIResponseSchema<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({
    success: z.boolean(),
    data: dataSchema.nullable().optional(),
    error: ErrorDetailSchema.nullable().optional(),
    request_id: z.string().nullable().optional(),
  });
}

export const HealthResponseSchema = createAPIResponseSchema(HealthStatusSchema);
export const ReadinessResponseSchema = createAPIResponseSchema(ReadinessStatusSchema);
export const SchemaStatusResponseSchema = createAPIResponseSchema(SchemaStatusSchema);
export const TableListResponseSchema = createAPIResponseSchema(z.array(TableSummarySchema));
export const TableDetailResponseSchema = createAPIResponseSchema(TableModelSchema);
export const PreparationJobResponseSchema = createAPIResponseSchema(PreparationJobStateSchema);
export const QueryWorkflowResponseSchema = createAPIResponseSchema(QueryWorkflowResultSchema);

export type ColumnModel = z.infer<typeof ColumnModelSchema>;
export type TableModel = z.infer<typeof TableModelSchema>;
export type TableSummary = z.infer<typeof TableSummarySchema>;
export type DatabaseCatalog = z.infer<typeof DatabaseCatalogSchema>;
export type PreparationJobState = z.infer<typeof PreparationJobStateSchema>;
export type SchemaStatus = z.infer<typeof SchemaStatusSchema>;
export type ReadinessStatus = z.infer<typeof ReadinessStatusSchema>;
export type QueryWorkflowResult = z.infer<typeof QueryWorkflowResultSchema>;
export type StepTrace = z.infer<typeof StepTraceSchema>;
export type QueryExecutionResult = z.infer<typeof QueryExecutionResultSchema>;
export type RouteResult = z.infer<typeof RouteResultSchema>;

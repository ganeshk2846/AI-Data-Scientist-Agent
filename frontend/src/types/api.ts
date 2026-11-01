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

// Phase 4 Agent Contracts
export const RouteResultSchema = z.object({
  intent: z.enum(["descriptive", "comparative", "trend", "diagnostic", "predictive", "prescriptive"]),
  confidence: z.number(),
  complexity: z.enum(["simple", "medium", "complex"]),
  reasoning: z.string(),
  target_domains: z.array(z.string()).default([]),
  suggested_entities: z.array(z.string()).default([]),
});

export const AnswerabilityAssessmentSchema = z.object({
  is_answerable: z.boolean(),
  confidence: z.number(),
  abstention_type: z.string().nullable().optional(),
  refusal_reason: z.string().nullable().optional(),
  available_alternatives: z.array(z.string()).default([]),
});

export const ClarificationOptionSchema = z.object({
  option_id: z.string(),
  label: z.string(),
  description: z.string(),
  inferred_query: z.string(),
});

export const ClarificationResponseSchema = z.object({
  needs_clarification: z.boolean(),
  question: z.string().nullable().optional(),
  ambiguity_reason: z.string().nullable().optional(),
  options: z.array(ClarificationOptionSchema).default([]),
  default_interpretation: z.string().nullable().optional(),
});

export const PlanStepSchema = z.object({
  step_id: z.string(),
  tool_name: z.string(),
  description: z.string(),
  dependencies: z.array(z.string()).default([]),
  arguments: z.record(z.any()).default({}),
  status: z.enum(["pending", "running", "succeeded", "failed", "skipped"]),
  output: z.any().nullable().optional(),
  error: z.string().nullable().optional(),
  duration_ms: z.number().default(0.0),
});

export const ExecutionPlanSchema = z.object({
  plan_id: z.string(),
  goal: z.string(),
  steps: z.array(PlanStepSchema),
  current_step_id: z.string().nullable().optional(),
  created_at: z.string(),
});

export const RepairAttemptSchema = z.object({
  attempt_number: z.number(),
  original_sql: z.string(),
  error_message: z.string(),
  repaired_sql: z.string(),
  explanation: z.string(),
  success: z.boolean(),
  validation_passed: z.boolean(),
});

export const ChartSpecificationSchema = z.object({
  chart_type: z.enum(["bar", "line", "scatter", "pie", "table"]),
  title: z.string(),
  x_axis_field: z.string().nullable().optional(),
  y_axis_field: z.string().nullable().optional(),
  category_field: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  data_points_count: z.number().default(0),
  fallback_to_table: z.boolean().default(false),
  subtitle: z.string().nullable().optional(),
  color_field: z.string().nullable().optional(),
  units: z.string().nullable().optional(),
  alt_text: z.string().nullable().optional(),
  plotly_data: z.array(z.record(z.any())).default([]),
  plotly_layout: z.record(z.any()).default({}),
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


export const ProvenanceInfoSchema = z.object({
  source_dataset: z.string().default("ecommerce.sqlite"),
  time_window: z.string().default("2023-01-01 to 2025-12-31"),
  record_count: z.number().default(0),
  computed_at: z.string(),
  method_name: z.string(),
  assumptions: z.array(z.string()).default([]),
});

export const PeriodComparisonResultSchema = z.object({
  metric_name: z.string(),
  period_a_label: z.string(),
  period_a_value: z.number(),
  period_b_label: z.string(),
  period_b_value: z.number(),
  delta_absolute: z.number(),
  delta_percentage: z.number(),
  dimension_breakdown: z.array(z.record(z.any())).default([]),
});

export const AnomalyPointSchema = z.object({
  date: z.string(),
  actual_value: z.number(),
  expected_value: z.number(),
  z_score: z.number(),
  is_anomaly: z.boolean(),
  severity: z.string(),
  quality_flag: z.string().nullable().optional(),
});

export const AnomalyDetectionResultSchema = z.object({
  metric_name: z.string(),
  threshold: z.number(),
  total_data_points: z.number(),
  anomaly_count: z.number(),
  anomalies: z.array(AnomalyPointSchema),
  method: z.string(),
  quality_warning: z.string().nullable().optional(),
});

export const DriverContributionSchema = z.object({
  dimension_value: z.string(),
  period_a_value: z.number(),
  period_b_value: z.number(),
  delta: z.number(),
  pct_of_total_delta: z.number(),
  direction: z.string(),
});

export const DriverAnalysisResultSchema = z.object({
  metric_name: z.string(),
  dimension: z.string(),
  total_delta: z.number(),
  sample_size: z.number(),
  drivers: z.array(DriverContributionSchema),
  causal_claim_disclaimer: z.string(),
});

export const ForecastPointSchema = z.object({
  date: z.string(),
  point_forecast: z.number(),
  lower_bound_80: z.number(),
  upper_bound_80: z.number(),
  lower_bound_95: z.number(),
  upper_bound_95: z.number(),
});

export const ForecastResultSchema = z.object({
  metric_name: z.string(),
  horizon_periods: z.number(),
  frequency: z.string(),
  points: z.array(ForecastPointSchema),
  model_used: z.string(),
  backtest_mae: z.number().nullable().optional(),
  backtest_rmse: z.number().nullable().optional(),
  backtest_mape_pct: z.number().nullable().optional(),
  is_sufficient_data: z.boolean().default(true),
  limitations: z.array(z.string()).default([]),
  suggested_followups: z.array(z.string()).default([]),
});

export const ScenarioResultSchema = z.object({
  target_metric: z.string(),
  baseline_value: z.number(),
  simulated_value: z.number(),
  delta_absolute: z.number(),
  delta_percentage: z.number(),
  assumptions_applied: z.record(z.any()),
  sensitivities: z.array(z.record(z.any())).default([]),
});

export const SegmentChurnRiskSchema = z.object({
  segment_name: z.string(),
  customer_count: z.number(),
  active_count: z.number(),
  churned_count: z.number(),
  churn_rate_pct: z.number(),
  total_historical_spend: z.number(),
  revenue_at_risk: z.number(),
  confidence_interval_low: z.number(),
  confidence_interval_high: z.number(),
  actionability_rank: z.number(),
});

export const ChurnAnalysisResultSchema = z.object({
  cutoff_date: z.string(),
  inactivity_threshold_days: z.number(),
  total_customers_analyzed: z.number(),
  total_revenue_at_risk: z.number(),
  segments: z.array(SegmentChurnRiskSchema),
  observations: z.array(z.string()).default([]),
});

export const OptimizationResultSchema = z.object({
  objective: z.string(),
  total_budget: z.number(),
  allocations: z.record(z.number()),
  expected_total_revenue: z.number(),
  constraints_satisfied: z.boolean(),
  status: z.string(),
  notes: z.array(z.string()).default([]),
});

export const AnalysisToolResultSchema = z.object({
  tool_name: z.string(),
  analysis_type: z.string(),
  success: z.boolean(),
  provenance: ProvenanceInfoSchema,
  abstain_reason: z.string().nullable().optional(),
  period_comparison: PeriodComparisonResultSchema.nullable().optional(),
  anomaly_detection: AnomalyDetectionResultSchema.nullable().optional(),
  driver_analysis: DriverAnalysisResultSchema.nullable().optional(),
  forecast: ForecastResultSchema.nullable().optional(),
  scenario: ScenarioResultSchema.nullable().optional(),
  churn_risk: ChurnAnalysisResultSchema.nullable().optional(),
  optimization: OptimizationResultSchema.nullable().optional(),
});

export const MultiAgentWorkflowResultSchema = z.object({
  run_id: z.string(),
  query: z.string(),
  route: RouteResultSchema,
  answerability: AnswerabilityAssessmentSchema,
  clarification: ClarificationResponseSchema.nullable().optional(),
  plan: ExecutionPlanSchema.nullable().optional(),
  selected_tables: z.array(z.string()).default([]),
  sanitized_sql: z.string().nullable().optional(),
  query_result: QueryExecutionResultSchema.nullable().optional(),
  chart_spec: ChartSpecificationSchema.nullable().optional(),
  analysis_result: AnalysisToolResultSchema.nullable().optional(),
  verification: VerificationResultSchema.nullable().optional(),
  repair_attempts: z.array(RepairAttemptSchema).default([]),
  composed_answer: z.string(),
  key_findings: z.array(z.string()).default([]),
  limitations: z.array(z.string()).default([]),
  suggested_followups: z.array(z.string()).default([]),
  trace_steps: z.array(StepTraceSchema).default([]),
  total_duration_ms: z.number(),
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
export const BusinessMetricSchema = z.object({
  name: z.string(),
  display_name: z.string(),
  formula_sql: z.string(),
  plain_description: z.string(),
  primary_tables: z.array(z.string()),
  filters_applied: z.array(z.string()).default([]),
  business_caveat: z.string().nullable().optional(),
});

export const LinkedValueSchema = z.object({
  matched_text: z.string(),
  table_name: z.string(),
  column_name: z.string(),
  target_value: z.string(),
  confidence: z.number(),
  filter_expression: z.string(),
});

export const RetrievedTableSchema = z.object({
  table_name: z.string(),
  domain: z.string(),
  rrf_score: z.number(),
  bm25_score: z.number(),
  bm25_rank: z.number(),
  embedding_score: z.number(),
  embedding_rank: z.number(),
  is_expanded_join: z.boolean().default(false),
  expansion_reason: z.string().nullable().optional(),
});

export const HybridRetrievalResultSchema = z.object({
  query: z.string(),
  retrieved_tables: z.array(RetrievedTableSchema),
  selected_table_names: z.array(z.string()),
  minimal_schema_prompt: z.string(),
});

export const RetrievalDiagnosticPayloadSchema = z.object({
  query: z.string(),
  hybrid_result: HybridRetrievalResultSchema,
  linked_values: z.array(LinkedValueSchema),
  relevant_metrics: z.array(BusinessMetricSchema),
});

export const BusinessMetricsListResponseSchema = createAPIResponseSchema(z.array(BusinessMetricSchema));
export const RetrievalDiagnosticResponseSchema = createAPIResponseSchema(RetrievalDiagnosticPayloadSchema);

export type BusinessMetric = z.infer<typeof BusinessMetricSchema>;
export type LinkedValue = z.infer<typeof LinkedValueSchema>;
export type RetrievedTable = z.infer<typeof RetrievedTableSchema>;
export type HybridRetrievalResult = z.infer<typeof HybridRetrievalResultSchema>;
export type RetrievalDiagnosticPayload = z.infer<typeof RetrievalDiagnosticPayloadSchema>;

export const MultiAgentWorkflowResponseSchema = createAPIResponseSchema(MultiAgentWorkflowResultSchema);

export type ColumnModel = z.infer<typeof ColumnModelSchema>;
export type TableModel = z.infer<typeof TableModelSchema>;
export type TableSummary = z.infer<typeof TableSummarySchema>;
export type DatabaseCatalog = z.infer<typeof DatabaseCatalogSchema>;
export type PreparationJobState = z.infer<typeof PreparationJobStateSchema>;
export type SchemaStatus = z.infer<typeof SchemaStatusSchema>;
export type ReadinessStatus = z.infer<typeof ReadinessStatusSchema>;
export type MultiAgentWorkflowResult = z.infer<typeof MultiAgentWorkflowResultSchema>;
export type ExecutionPlan = z.infer<typeof ExecutionPlanSchema>;
export type PlanStep = z.infer<typeof PlanStepSchema>;
export type ChartSpecification = z.infer<typeof ChartSpecificationSchema>;
export type RepairAttempt = z.infer<typeof RepairAttemptSchema>;
export type ClarificationResponse = z.infer<typeof ClarificationResponseSchema>;
export type ClarificationOption = z.infer<typeof ClarificationOptionSchema>;

export type AnalysisToolResult = z.infer<typeof AnalysisToolResultSchema>;
export type AnomalyPoint = z.infer<typeof AnomalyPointSchema>;
export type ForecastPoint = z.infer<typeof ForecastPointSchema>;
export type SegmentChurnRisk = z.infer<typeof SegmentChurnRiskSchema>;

export type QueryExecutionResult = z.infer<typeof QueryExecutionResultSchema>;

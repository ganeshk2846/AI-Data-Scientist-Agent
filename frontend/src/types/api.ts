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
  session_id: z.string().default("default_session"),
  query: z.string(),
  standalone_query: z.string().nullable().optional(),
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


// Observability and Telemetry Schemas
export const RunTraceRecordSchema = z.object({
  run_id: z.string(),
  session_id: z.string(),
  query: z.string(),
  intent: z.string(),
  latency_ms: z.number(),
  sql_executed: z.string().nullable().optional(),
  row_count: z.number(),
  cost_estimate_usd: z.number(),
  error_class: z.string().nullable().optional(),
  verification_status: z.string(),
  created_at: z.string(),
});

export const ObservabilityMetricsSchema = z.object({
  total_runs: z.number(),
  success_rate_pct: z.number(),
  latency_p50_ms: z.number(),
  latency_p95_ms: z.number(),
  latency_p99_ms: z.number(),
  avg_latency_ms: z.number(),
  safety_block_count: z.number(),
  error_classes_breakdown: z.record(z.number()).default({}),
});

export const ObservabilityMetricsResponseSchema = createAPIResponseSchema(ObservabilityMetricsSchema);
export const RunTraceListResponseSchema = createAPIResponseSchema(z.array(RunTraceRecordSchema));

export type RunTraceRecord = z.infer<typeof RunTraceRecordSchema>;
export type ObservabilityMetrics = z.infer<typeof ObservabilityMetricsSchema>;

// Memory and Sessions Schemas
export const TurnModelSchema = z.object({
  turn_id: z.string(),
  session_id: z.string(),
  role: z.string(),
  content: z.string(),
  standalone_rewrite: z.string().nullable().optional(),
  sql_executed: z.string().nullable().optional(),
  artifact_ref_id: z.string().nullable().optional(),
  created_at: z.string(),
});

export const SessionModelSchema = z.object({
  session_id: z.string(),
  user_id: z.string().default("default_user"),
  title: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  active_frame: z.any().optional(),
});

export const SessionListResponseSchema = createAPIResponseSchema(z.array(SessionModelSchema));
export const SessionDetailResponseSchema = createAPIResponseSchema(
  z.object({
    session: SessionModelSchema,
    turns: z.array(TurnModelSchema),
  })
);

export type TurnModel = z.infer<typeof TurnModelSchema>;
export type SessionModel = z.infer<typeof SessionModelSchema>;


// =====================================================================
// Phase 4: Domain-Independent Analytical Intelligence Contracts
// =====================================================================

export const IntentCategorySchema = z.enum([
  "DESCRIPTIVE",
  "DIAGNOSTIC",
  "PREDICTIVE",
  "PRESCRIPTIVE",
  "SQL_LOOKUP",
]);
export type IntentCategory = z.infer<typeof IntentCategorySchema>;

export const ComplexityLevelSchema = z.enum(["SIMPLE", "MODERATE", "COMPLEX", "ADVANCED"]);
export type ComplexityLevel = z.infer<typeof ComplexityLevelSchema>;

export const ClaimTypeSchema = z.enum([
  "NUMERICAL",
  "DIRECTIONAL",
  "COMPARATIVE",
  "STATISTICAL",
  "DRIVER_CONTRIBUTION",
  "CAUSAL",
  "PREDICTIVE",
  "RECOMMENDATION",
]);
export type ClaimType = z.infer<typeof ClaimTypeSchema>;

export const StructuredClaimSchema = z.object({
  claim_id: z.string(),
  claim_type: ClaimTypeSchema,
  statement: z.string(),
  verified: z.boolean().default(false),
  evidence_reference: z.string().nullable().optional(),
  discrepancy: z.string().nullable().optional(),
});
export type StructuredClaim = z.infer<typeof StructuredClaimSchema>;

export const FaithfulnessReportSchema = z.object({
  is_faithful: z.boolean(),
  total_claims_checked: z.number(),
  verified_claims: z.number(),
  discrepancies: z.array(z.string()).default([]),
  confidence_discount: z.number().default(0.0),
  structured_claims: z.array(StructuredClaimSchema).default([]),
});
export type FaithfulnessReport = z.infer<typeof FaithfulnessReportSchema>;

export const StandardizedAnalyticalResultSchema = z.object({
  analysis_id: z.string(),
  analytical_type: IntentCategorySchema,
  analysis_question: z.string(),
  success: z.boolean(),
  selected_methods: z.array(z.string()).default([]),
  source_tables: z.array(z.string()).default([]),
  source_columns: z.array(z.string()).default([]),
  executed_queries: z.array(z.string()).default([]),
  result_data: z.array(z.record(z.any())).default([]),
  computed_metrics: z.record(z.any()).default({}),
  model_information: z.record(z.any()).default({}),
  validation_results: z.record(z.any()).default({}),
  faithfulness: FaithfulnessReportSchema.nullable().optional(),
  confidence_score: z.number().default(1.0),
  uncertainty_notes: z.array(z.string()).default([]),
  findings: z.array(z.string()).default([]),
  limitations: z.array(z.string()).default([]),
  recommended_next_steps: z.array(z.string()).default([]),
  visualization_config: z.record(z.any()).nullable().optional(),
  abstain_reason: z.string().nullable().optional(),
  created_at: z.string().optional(),
});
export type StandardizedAnalyticalResult = z.infer<typeof StandardizedAnalyticalResultSchema>;

export const IntentClassificationResultSchema = z.object({
  primary_intent: IntentCategorySchema,
  complexity: ComplexityLevelSchema,
  confidence_score: z.number(),
  all_probabilities: z.record(z.number()).default({}),
  is_ambiguous: z.boolean().default(false),
  requires_clarification: z.boolean().default(false),
  suggested_clarification: z.string().nullable().optional(),
  recommended_methods: z.array(z.string()).default([]),
  is_composite: z.boolean().default(false),
  composite_intents: z.array(IntentCategorySchema).default([]),
  execution_sequence: z.array(z.string()).default([]),
});
export type IntentClassificationResult = z.infer<typeof IntentClassificationResultSchema>;

export const AnalyticalPlanSchema = z.object({
  plan_id: z.string(),
  question: z.string(),
  intent: IntentCategorySchema,
  complexity: ComplexityLevelSchema,
  analytical_objective: z.string(),
  relevant_tables: z.array(z.string()).default([]),
  required_columns: z.record(z.array(z.string())).default({}),
  relevant_metrics: z.array(z.string()).default([]),
  filters: z.array(z.record(z.any())).default([]),
  time_dimension: z.string().nullable().optional(),
  target_variable: z.string().nullable().optional(),
  candidate_methods: z.array(z.string()).default([]),
  selected_method: z.string(),
  data_extraction_sql: z.string().nullable().optional(),
  validation_requirements: z.array(z.string()).default([]),
  expected_output_format: z.string().default("table_and_chart"),
  is_executable: z.boolean().default(true),
  abstain_reason: z.string().nullable().optional(),
});
export type AnalyticalPlan = z.infer<typeof AnalyticalPlanSchema>;

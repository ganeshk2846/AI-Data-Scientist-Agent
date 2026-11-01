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

export type HealthStatus = z.infer<typeof HealthStatusSchema>;
export type DatabaseReadiness = z.infer<typeof DatabaseReadinessSchema>;
export type LLMReadiness = z.infer<typeof LLMReadinessSchema>;
export type ReadinessStatus = z.infer<typeof ReadinessStatusSchema>;
export type ErrorDetail = z.infer<typeof ErrorDetailSchema>;
export type APIResponse<T> = {
  success: boolean;
  data?: T | null;
  error?: ErrorDetail | null;
  request_id?: string | null;
};

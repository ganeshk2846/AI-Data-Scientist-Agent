import { ReadinessResponseSchema, ReadinessStatus } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchReadiness(): Promise<ReadinessStatus> {
  const url = `${API_BASE_URL}/api/v1/ready`;
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const json = await res.json();
    const parsed = ReadinessResponseSchema.safeParse(json);

    if (!parsed.success) {
      console.error("Zod Validation Failed:", parsed.error);
      throw new Error(`Schema validation error: ${parsed.error.message}`);
    }

    if (!parsed.data.data) {
      throw new Error(parsed.data.error?.message || "Received empty readiness data from server");
    }

    return parsed.data.data;
  } catch (err: any) {
    console.error("Fetch readiness failed:", err);
    throw err;
  }
}

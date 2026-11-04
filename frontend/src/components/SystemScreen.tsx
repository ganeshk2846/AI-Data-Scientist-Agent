"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchReadiness } from "@/lib/api";
import { HealthReadinessCard } from "@/components/HealthReadinessCard";

/**
 * The System destination.
 *
 * It owns its own readiness query rather than being handed one by a parent, so
 * the route renders on its own and its Retry control genuinely refetches.
 */
export function SystemScreen() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    refetchInterval: 30_000,
  });

  return (
    <HealthReadinessCard
      data={data}
      isLoading={isLoading}
      isError={isError}
      error={error as Error | null}
      onRefresh={() => refetch()}
    />
  );
}

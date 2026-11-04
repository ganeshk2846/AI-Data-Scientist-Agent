"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import { fetchSetupStatus } from "@/lib/api";

interface HeaderProps {
  isReady?: boolean;
}

/**
 * The bar on the setup and connection screens, which sit outside the app
 * shell. A plain bar: the product's name, the scope it is connected to, and
 * its state. No gradient, no glass, no glow.
 */
export function Header({ isReady }: HeaderProps) {
  const { data } = useQuery({
    queryKey: ["setupStatus"],
    queryFn: fetchSetupStatus,
    refetchInterval: 15_000,
  });

  const online = isReady ?? data?.chat_ready ?? false;

  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)] bg-ground">
      <div className="mx-auto flex h-12 max-w-[1200px] items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-2">
          <a href="/" className="text-label font-medium text-text">
            AI for BI
          </a>
          {data?.database?.name ? (
            <>
              <span aria-hidden="true" className="text-faint">
                /
              </span>
              <span className="truncate font-mono text-label text-muted">{data.database.name}</span>
            </>
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-3">
          {data?.llm?.model ? (
            <span className="hidden truncate font-mono text-label text-muted sm:inline">{data.llm.model}</span>
          ) : null}
          <span className="flex items-center gap-1.5 text-label text-muted">
            <span
              aria-hidden="true"
              className={clsx("h-1.5 w-1.5 rounded-full", online ? "bg-positive" : "bg-[var(--control)]")}
            />
            {online ? "Ready" : "Connecting"}
          </span>
        </div>
      </div>
    </header>
  );
}

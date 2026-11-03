"use client";

import React, { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PreparationProgress } from "@/components/setup/PreparationProgress";
import { Header } from "@/components/Header";
import { RefreshCw } from "lucide-react";

function PreparingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId") || undefined;

  return (
    <PreparationProgress
      initialJobId={jobId}
      onComplete={() => router.push("/")}
    />
  );
}

export default function PreparingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Header />
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <Suspense
          fallback={
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <RefreshCw className="w-4 h-4 animate-spin text-primary" />
              <span>Loading preparation workspace...</span>
            </div>
          }
        >
          <PreparingContent />
        </Suspense>
      </main>
    </div>
  );
}

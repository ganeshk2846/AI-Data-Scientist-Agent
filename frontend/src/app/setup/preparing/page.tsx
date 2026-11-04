"use client";

import React, { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PreparationProgress } from "@/components/setup/PreparationProgress";
import { Header } from "@/components/Header";

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
    <div className="flex min-h-screen flex-col bg-ground">
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 items-start justify-center px-4 py-10 sm:px-6">
        <Suspense
          fallback={
            <p className="text-body text-muted">Loading the preparation view…</p>
          }
        >
          <PreparingContent />
        </Suspense>
      </main>
    </div>
  );
}

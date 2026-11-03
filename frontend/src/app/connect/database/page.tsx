"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { DatabaseConnectionForm } from "@/components/setup/DatabaseConnectionForm";
import { Header } from "@/components/Header";

export default function ConnectDatabasePage() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Header />
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <DatabaseConnectionForm
          onSuccess={(job) => {
            router.push(`/setup/preparing?jobId=${job.job_id}`);
          }}
          onNavigateToPreparation={(jobId) => {
            router.push(`/setup/preparing?jobId=${jobId}`);
          }}
        />
      </main>
    </div>
  );
}

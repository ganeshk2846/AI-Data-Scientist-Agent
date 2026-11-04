"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { DatabaseConnectionForm } from "@/components/setup/DatabaseConnectionForm";
import { Header } from "@/components/Header";

export default function ConnectDatabasePage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-ground">
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 items-start justify-center px-4 py-10 sm:px-6">
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


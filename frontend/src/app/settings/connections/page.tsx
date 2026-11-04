"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { ConnectionManager } from "@/components/setup/ConnectionManager";
import { Header } from "@/components/Header";

export default function ConnectionsSettingsPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-ground">
      <Header />
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-4 py-10 sm:px-6">
        <ConnectionManager
          onNavigateToPreparation={(jobId) => router.push(`/setup/preparing?jobId=${jobId}`)}
        />
      </main>
    </div>
  );
}


"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { ConnectionManager } from "@/components/setup/ConnectionManager";
import { Header } from "@/components/Header";

export default function ConnectionsSettingsPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Header />
      <main className="flex-1 p-4 sm:p-8">
        <ConnectionManager
          onNavigateToPreparation={(jobId) => router.push(`/setup/preparing?jobId=${jobId}`)}
        />
      </main>
    </div>
  );
}

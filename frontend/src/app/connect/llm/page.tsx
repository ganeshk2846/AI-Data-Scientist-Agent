"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { GroqConnectionForm } from "@/components/setup/GroqConnectionForm";
import { Header } from "@/components/Header";

export default function ConnectLLMPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Header />
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <GroqConnectionForm
          showContinueButton={true}
          onContinue={() => router.push("/connect/database")}
          onSuccess={() => router.push("/connect/database")}
        />
      </main>
    </div>
  );
}


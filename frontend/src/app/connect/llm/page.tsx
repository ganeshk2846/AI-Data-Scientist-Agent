"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { GroqConnectionForm } from "@/components/setup/GroqConnectionForm";
import { Header } from "@/components/Header";

export default function ConnectLLMPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-ground">
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 items-start justify-center px-4 py-10 sm:px-6">
        <GroqConnectionForm
          showContinueButton={true}
          onContinue={() => router.push("/connect/database")}
          onSuccess={() => router.push("/connect/database")}
        />
      </main>
    </div>
  );
}


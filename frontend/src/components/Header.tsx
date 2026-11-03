"use client";

import React from "react";
import Link from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchSetupStatus } from "@/lib/api";
import { Sparkles, ShieldCheck, Database, Cpu, Settings } from "lucide-react";
import { Badge } from "./ui/Badge";

export interface HeaderProps {
  isReady?: boolean;
  version?: string;
}

export function Header({ isReady, version = "0.1.0" }: HeaderProps) {
  const { data: setupData } = useQuery({
    queryKey: ["setupStatus"],
    queryFn: fetchSetupStatus,
    refetchInterval: 15000,
  });

  const groqModel = setupData?.llm?.model || "llama-3.3-70b-versatile";
  const dbName = setupData?.database?.name || "ecommerce.db";
  const dbEngine = setupData?.database?.engine || "sqlite";
  const isOnline = isReady ?? setupData?.chat_ready;

  return (
    <header className="border-b border-border/80 bg-card/75 backdrop-blur-md px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-40 shadow-sm">
      <div className="flex items-center gap-3">
        <a href="/" className="p-2 rounded-xl bg-gradient-to-br from-primary/30 to-primary/10 text-primary border border-primary/20 shadow-sm hover:opacity-90 transition-opacity">
          <Sparkles className="w-5 h-5" />
        </a>
        <div>
          <div className="flex items-center gap-2">
            <a href="/" className="font-bold text-sm sm:text-base tracking-tight text-foreground hover:text-primary transition-colors">
              AI for BI Data Scientist Agent
            </a>
            <Badge variant="mono" size="xs">
              v{version}
            </Badge>
            <Badge variant="success" size="xs" className="hidden md:inline-flex gap-1 font-mono">
              <ShieldCheck className="w-3 h-3" />
              <span>mode=ro</span>
            </Badge>
          </div>
          <p className="text-[11px] text-muted-foreground hidden lg:block">
            Enterprise conversational BI with schema grounding & AST-validated safe SQL
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2.5 text-xs">
        {/* Active Groq Badge */}
        {setupData?.llm?.connected && (
          <a
            href="/settings/connections"
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-background/80 border border-border/70 hover:border-primary/40 transition-colors"
            title="Groq AI Inference Provider"
          >
            <Cpu className="w-3 h-3 text-primary" />
            <span className="font-mono text-[11px] text-foreground truncate max-w-[140px]">
              {groqModel}
            </span>
          </a>
        )}

        {/* Active Database Badge */}
        {setupData?.database?.connected && (
          <a
            href="/settings/connections"
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-background/80 border border-border/70 hover:border-primary/40 transition-colors"
            title="Active Read-Only Business Database"
          >
            <Database className="w-3 h-3 text-success" />
            <span className="font-mono text-[11px] text-foreground truncate max-w-[120px]">
              {dbName}
            </span>
            <Badge variant="mono" size="xs" className="text-[9px] px-1 py-0 uppercase">
              {dbEngine}
            </Badge>
          </a>
        )}

        {/* Connections Settings Link */}
        <a
          href="/settings/connections"
          className="p-1.5 rounded-lg border border-border/80 bg-background/60 hover:bg-background text-muted-foreground hover:text-foreground transition-colors"
          title="Connection Settings"
        >
          <Settings className="w-4 h-4" />
        </a>

        {/* Backend / Chat Status Pill */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-background/60 border border-border/80 shadow-inner">
          <span
            className={`w-2 h-2 rounded-full ${
              isOnline ? "bg-success animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-warning"
            }`}
          />
          <span className="font-medium text-foreground text-[10px] sm:text-[11px]">
            {isOnline ? "Ready" : "Connecting"}
          </span>
        </div>
      </div>
    </header>
  );
}

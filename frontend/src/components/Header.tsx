"use client";

import React from "react";
import { Sparkles, ShieldCheck } from "lucide-react";
import { Badge } from "./ui/Badge";

export interface HeaderProps {
  isReady?: boolean;
  version?: string;
}

export function Header({ isReady, version = "0.1.0" }: HeaderProps) {
  return (
    <header className="border-b border-border/80 bg-card/75 backdrop-blur-md px-6 py-3.5 flex items-center justify-between sticky top-0 z-40 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-br from-primary/30 to-primary/10 text-primary border border-primary/20 shadow-sm">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-base tracking-tight text-foreground">
              AI for BI Data Scientist Agent
            </h1>
            <Badge variant="mono" size="xs">
              v{version}
            </Badge>
            <Badge variant="success" size="xs" className="hidden sm:inline-flex gap-1 font-mono">
              <ShieldCheck className="w-3 h-3" />
              <span>mode=ro</span>
            </Badge>
          </div>
          <p className="text-[11px] text-muted-foreground hidden sm:block">
            Enterprise conversational BI with schema grounding & AST-validated safe SQL
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-background/60 border border-border/80 shadow-inner">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isReady ? "bg-success animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-warning"
            }`}
          />
          <span className="font-medium text-foreground text-[11px]">
            {isReady ? "Backend Online" : "Connecting..."}
          </span>
        </div>
      </div>
    </header>
  );
}

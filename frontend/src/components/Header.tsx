"use client";

import { Activity, Database, Sparkles } from "lucide-react";

interface HeaderProps {
  isReady?: boolean;
  version?: string;
}

export function Header({ isReady, version = "0.1.0" }: HeaderProps) {
  return (
    <header className="border-b border-border bg-card/60 backdrop-blur px-6 py-4 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="p-2 rounded-lg bg-primary/10 text-primary">
          <Sparkles className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-semibold text-lg tracking-tight text-foreground">
              AI for BI Data Scientist Agent
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-border text-muted-foreground font-mono">
              v{version}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Enterprise conversational BI with schema grounding & AST-validated SQL
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-4 text-xs">
        <div className="flex items-center space-x-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isReady ? "bg-success animate-pulse" : "bg-warning"
            }`}
          />
          <span className="font-medium text-foreground">
            {isReady ? "Backend Online" : "Connecting..."}
          </span>
        </div>
      </div>
    </header>
  );
}

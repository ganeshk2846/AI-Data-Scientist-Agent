"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchLLMStatus,
  fetchSupportedModels,
  connectGroqLLM,
  disconnectGroqLLM,
} from "@/lib/api";
import { LLMModelInfo, LLMStatusData } from "@/types/api";
import {
  Sparkles,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Cpu,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

interface GroqConnectionFormProps {
  onSuccess?: (data: LLMStatusData) => void;
  showContinueButton?: boolean;
  onContinue?: () => void;
}

export function GroqConnectionForm({
  onSuccess,
  showContinueButton = true,
  onContinue,
}: GroqConnectionFormProps) {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [selectedModel, setSelectedModel] = useState("llama-3.3-70b-versatile");
  const [showKey, setShowKey] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch current LLM status
  const { data: statusData, isLoading: loadingStatus } = useQuery({
    queryKey: ["llmStatus"],
    queryFn: fetchLLMStatus,
  });

  // Fetch supported models
  const { data: modelsData, isLoading: loadingModels } = useQuery({
    queryKey: ["supportedModels"],
    queryFn: fetchSupportedModels,
  });

  useEffect(() => {
    if (statusData?.model) {
      setSelectedModel(statusData.model);
    }
  }, [statusData?.model]);

  // Connect mutation
  const connectMutation = useMutation({
    mutationFn: async () => {
      setErrorMessage(null);
      return await connectGroqLLM(apiKey, selectedModel);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["llmStatus"] });
      queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
      queryClient.invalidateQueries({ queryKey: ["readiness"] });
      setApiKey(""); // clear raw key immediately from local component state
      setIsEditing(false);
      if (onSuccess) {
        onSuccess(data);
      }
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Failed to validate Groq credentials.");
    },
  });

  // Disconnect mutation
  const disconnectMutation = useMutation({
    mutationFn: async () => {
      await disconnectGroqLLM();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llmStatus"] });
      queryClient.invalidateQueries({ queryKey: ["setupStatus"] });
      queryClient.invalidateQueries({ queryKey: ["readiness"] });
    },
  });

  const isConnected = statusData?.connected && statusData?.status === "CONNECTED";
  const models = modelsData || [
    {
      id: "llama-3.3-70b-versatile",
      name: "Llama 3.3 70B Versatile",
      context_window: 128000,
      is_recommended: true,
      description: "State-of-the-art multilingual model with 128k context and analytical reasoning",
    },
    {
      id: "openai/gpt-oss-120b",
      name: "GPT-OSS 120B",
      context_window: 8192,
      is_recommended: false,
      description: "High parameter open weights model with strong structured outputs",
    },
    {
      id: "llama-3.1-8b-instant",
      name: "Llama 3.1 8B Instant",
      context_window: 128000,
      is_recommended: false,
      description: "Ultra low latency inference optimized for high-throughput exploration",
    },
  ];

  return (
    <div className="bg-card border border-border/80 rounded-2xl p-6 sm:p-8 max-w-xl mx-auto shadow-lg space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-primary/10 text-primary border border-primary/20 shrink-0">
          <Sparkles className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Connect Your AI Model
            <Badge variant="primary" size="xs">
              Groq Cloud ONLY
            </Badge>
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Groq is the dedicated AI provider powered by ultra-low latency LPU inference. Enter your Groq API key to power SQL synthesis and autonomous analytical agents.
          </p>
        </div>
      </div>

      {/* Connected State Banner */}
      {isConnected && (
        <div className="p-4 rounded-xl bg-success/10 border border-success/30 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-success font-medium text-sm">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Groq API Connected</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="xs"
                onClick={() => setIsEditing(!isEditing)}
                className="text-xs text-foreground hover:bg-muted"
              >
                {isEditing ? "Cancel" : "Change Key / Model"}
              </Button>
              <Button
                variant="outline"
                size="xs"
                onClick={() => disconnectMutation.mutate()}
                isLoading={disconnectMutation.isPending}
                className="text-xs text-muted-foreground hover:text-destructive hover:border-destructive/40"
              >
                Disconnect
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-background/60 p-2.5 rounded-lg border border-border/50">
            <div>
              <span className="text-[10px] text-muted-foreground block">ACTIVE MODEL</span>
              <span className="text-foreground font-semibold">{statusData?.model}</span>
            </div>
            <div>
              <span className="text-[10px] text-muted-foreground block">MASKED CREDENTIAL</span>
              <span className="text-foreground">{statusData?.masked_key || "gsk_...****"}</span>
            </div>
          </div>

          {showContinueButton && !isEditing && (
            <div className="pt-2 flex justify-end">
              <Button
                variant="primary"
                size="sm"
                onClick={onContinue}
                icon={<ArrowRight className="w-4 h-4" />}
              >
                Continue to Database Connection
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Form Fields (Show if not connected or editing) */}
      {(!isConnected || isEditing) && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (apiKey.trim()) {
              connectMutation.mutate();
            }
          }}
          className="space-y-4"
        >
          {/* Provider Display */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              LLM Provider
            </label>
            <div className="p-3 rounded-xl bg-background/80 border border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-primary" />
                <span className="font-semibold text-sm text-foreground">Groq Cloud API</span>
              </div>
              <Badge variant="mono" size="xs" className="font-mono">
                OpenAI-Compatible
              </Badge>
            </div>
          </div>

          {/* Model Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
              <span>Select Groq Model</span>
              {loadingModels && <RefreshCw className="w-3 h-3 animate-spin text-muted-foreground" />}
            </label>
            <div className="space-y-2">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 transition-colors cursor-pointer"
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} {m.is_recommended ? "(Recommended)" : ""} — {(m.context_window / 1000).toFixed(0)}k context
                  </option>
                ))}
              </select>

              {/* Model Description Details */}
              {models.find((m) => m.id === selectedModel) && (
                <p className="text-[11px] text-muted-foreground px-1">
                  {models.find((m) => m.id === selectedModel)?.description}
                </p>
              )}
            </div>
          </div>

          {/* API Key Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
              <span>Groq API Key</span>
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-primary hover:underline"
              >
                Get API Key from Groq Console ↗
              </a>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted-foreground">
                <KeyRound className="w-4 h-4" />
              </div>
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="gsk_..."
                required
                className="w-full bg-background border border-border rounded-xl pl-10 pr-10 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/40 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-muted-foreground hover:text-foreground cursor-pointer"
                title={showKey ? "Hide API key" : "Show API key"}
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/80 px-1 pt-0.5">
              <ShieldCheck className="w-3.5 h-3.5 text-success" />
              <span>Keys are encrypted with Fernet symmetric cipher on backend. Never stored in browser.</span>
            </div>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/30 flex items-start gap-2.5 text-destructive text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-semibold block">Connection Error</span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full justify-center"
              isLoading={connectMutation.isPending}
              disabled={!apiKey.trim()}
              icon={<Sparkles className="w-4 h-4" />}
            >
              {connectMutation.isPending
                ? "Validating & Connecting..."
                : isConnected
                ? "Update & Reconnect Groq LLM"
                : "Test & Connect Groq LLM"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}


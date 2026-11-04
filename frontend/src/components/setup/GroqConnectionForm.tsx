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
import { messageFrom } from "@/lib/errors";

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
      if (onSuccess) {
        onSuccess(data);
      }
    },
    onError: (err: unknown) => {
      setErrorMessage(messageFrom(err, "Failed to validate Groq credentials."));
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
    <div className="bg-surface border border-[var(--border)] rounded-card p-6 sm:p-8 max-w-xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div>
          <h2 className="text-title font-semibold tracking-tight text-text flex items-center gap-2">
            Connect Your AI Model
            <Badge variant="primary" size="xs">
              Groq Cloud ONLY
            </Badge>
          </h2>
          <p className="text-label text-muted mt-1">
            Groq is the dedicated AI provider powered by ultra-low latency LPU inference. Enter your Groq API key to power SQL synthesis and autonomous analytical agents.
          </p>
        </div>
      </div>

      {/* Connected State Banner */}
      {isConnected && (
        <div className="p-4 rounded-card bg-surface border border-[var(--border)] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-positive font-medium text-body">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Groq API Connected</span>
            </div>
            <Button
              variant="outline"
              size="xs"
              onClick={() => disconnectMutation.mutate()}
              isLoading={disconnectMutation.isPending}
              className="text-label text-muted hover:text-negative hover:border-[var(--border)]"
            >
              Disconnect
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-2 text-label font-mono bg-ground p-2.5 rounded-control border border-[var(--border)]">
            <div>
              <span className="text-micro text-muted block">Active model</span>
              <span className="text-text font-semibold">{statusData?.model}</span>
            </div>
            <div>
              <span className="text-micro text-muted block">Masked credential</span>
              <span className="text-text">{statusData?.masked_key || "gsk_...****"}</span>
            </div>
          </div>

          {showContinueButton && (
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
      {!isConnected && (
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
            <label className="text-label font-semibold text-muted">
              LLM Provider
            </label>
            <div className="p-3 rounded-card bg-ground border border-[var(--border)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-text" />
                <span className="font-semibold text-body text-text">Groq Cloud API</span>
              </div>
              <Badge variant="mono" size="xs" className="font-mono">
                OpenAI-Compatible
              </Badge>
            </div>
          </div>

          {/* Model Selector */}
          <div className="space-y-1.5">
            <label className="text-label font-semibold text-muted flex items-center justify-between">
              <span>Select Groq Model</span>
              {loadingModels && <RefreshCw className="w-3 h-3 animate-spin text-muted" />}
            </label>
            <div className="space-y-2">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full bg-ground border border-[var(--border)] rounded-card px-3.5 py-2.5 text-body text-text focus:outline-none focus:ring-2 focus:ring-[var(--control)] transition-colors cursor-pointer"
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} {m.is_recommended ? "(Recommended)" : ""} — {(m.context_window / 1000).toFixed(0)}k context
                  </option>
                ))}
              </select>

              {/* Model Description Details */}
              {models.find((m) => m.id === selectedModel) && (
                <p className="text-micro text-muted px-1">
                  {models.find((m) => m.id === selectedModel)?.description}
                </p>
              )}
            </div>
          </div>

          {/* API Key Input */}
          <div className="space-y-1.5">
            <label className="text-label font-semibold text-muted flex items-center justify-between">
              <span>Groq API Key</span>
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noreferrer"
                className="text-micro text-text hover:underline"
              >
                Get API Key from Groq Console ↗
              </a>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-muted">
                <KeyRound className="w-4 h-4" />
              </div>
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="gsk_..."
                required
                className="w-full bg-ground border border-[var(--border)] rounded-card pl-10 pr-10 py-2.5 text-body text-text placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-[var(--control)] font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-muted hover:text-text cursor-pointer"
                title={showKey ? "Hide API key" : "Show API key"}
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <div className="flex items-center gap-1.5 text-micro text-muted/80 px-1 pt-0.5">
              <ShieldCheck className="w-3.5 h-3.5 text-positive" />
              <span>Keys are encrypted with Fernet symmetric cipher on backend. Never stored in browser.</span>
            </div>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="p-3 rounded-card bg-pill-negative-bg border border-[var(--border)] flex items-start gap-2.5 text-negative text-label">
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
              {connectMutation.isPending ? "Validating & Connecting..." : "Test & Connect Groq LLM"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}


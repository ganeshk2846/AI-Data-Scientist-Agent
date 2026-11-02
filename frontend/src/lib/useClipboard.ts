import { useState, useCallback } from "react";

export function useClipboard(timeout = 2000) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copy = useCallback(
    (text: string, id: string = "default") => {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), timeout);
      }
    },
    [timeout]
  );

  return { copiedId, copy, isCopied: (id: string = "default") => copiedId === id };
}


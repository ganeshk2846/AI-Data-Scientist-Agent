import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "ai_bi_active_session_id";

function generateSessionId(): string {
  return "sess-" + Math.random().toString(36).substring(2, 9);
}

export function useSession() {
  const [sessionId, setSessionId] = useState<string>("sess-default");
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && stored.startsWith("sess-")) {
        setSessionId(stored);
      } else {
        const fresh = generateSessionId();
        localStorage.setItem(STORAGE_KEY, fresh);
        setSessionId(fresh);
      }
    } catch {
      // Fallback if localStorage blocked
      setSessionId(generateSessionId());
    } finally {
      setIsReady(true);
    }
  }, []);

  const createNewSession = useCallback((): string => {
    const fresh = generateSessionId();
    try {
      localStorage.setItem(STORAGE_KEY, fresh);
    } catch {}
    setSessionId(fresh);
    return fresh;
  }, []);

  const switchSession = useCallback((targetId: string) => {
    try {
      localStorage.setItem(STORAGE_KEY, targetId);
    } catch {}
    setSessionId(targetId);
  }, []);

  return { sessionId, isReady, createNewSession, switchSession };
}


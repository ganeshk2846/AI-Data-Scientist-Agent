import { Activity, Database, MessageSquare, ShieldCheck } from "lucide-react";

export type DestinationKey = "ask" | "data" | "activity" | "system";

export interface DestinationDef {
  key: DestinationKey;
  /** A real route, so the rail works before React hydrates — and without it. */
  href: string;
  label: string;
  /** What the destination is for, used as the tooltip's second line. */
  hint: string;
  icon: typeof MessageSquare;
}

/**
 * The four destinations, each a real route.
 *
 * They were state in a single page before: a click swapped a React state value
 * and rewrote the query string. That works only while the bundle is healthy —
 * when hydration does not happen the whole rail is dead HTML and every icon is
 * furniture. A route is navigable by the browser alone, so the rail cannot
 * stop working.
 */
export const DESTINATIONS: DestinationDef[] = [
  { key: "ask", href: "/", label: "Ask", hint: "Ask the warehouse a question", icon: MessageSquare },
  { key: "data", href: "/catalog", label: "Data", hint: "Tables, columns and metrics", icon: Database },
  { key: "activity", href: "/activity", label: "Activity", hint: "Runs, latency and stages", icon: Activity },
  { key: "system", href: "/system", label: "System", hint: "Connection and readiness", icon: ShieldCheck },
];

/** The destination a path belongs to, so the rail can mark where the reader is. */
export function destinationForPath(pathname: string | null): DestinationKey {
  if (!pathname) return "ask";
  if (pathname.startsWith("/catalog")) return "data";
  if (pathname.startsWith("/activity")) return "activity";
  if (pathname.startsWith("/system")) return "system";
  return "ask";
}

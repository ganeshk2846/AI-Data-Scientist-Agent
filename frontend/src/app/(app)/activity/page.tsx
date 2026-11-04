import type { Metadata } from "next";
import { ObservabilityDashboard } from "@/components/ObservabilityDashboard";

export const metadata: Metadata = {
  title: "Activity — AI for BI",
  description: "Every run the agent has answered: latency, verification status and the stages each one spent its time in.",
};

export default function ActivityPage() {
  return <ObservabilityDashboard />;
}

import type { Metadata } from "next";
import { SystemScreen } from "@/components/SystemScreen";

export const metadata: Metadata = {
  title: "System — AI for BI",
  description: "What is connected: the warehouse, its read-only guarantee, and the model answering questions.",
};

export default function SystemPage() {
  return <SystemScreen />;
}

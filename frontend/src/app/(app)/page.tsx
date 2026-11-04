import type { Metadata } from "next";
import { ChatInterface } from "@/components/ChatInterface";
import { SetupReadinessGuard } from "@/components/setup/SetupReadinessGuard";

export const metadata: Metadata = {
  title: "Ask the data — AI for BI",
  description:
    "Ask a business question in plain language and get verified analysis: headline figures with their uncertainty, a chart, the rows, and the SQL that produced every number.",
};

/** The thread. The setup wizard gates this destination only — never the rail. */
export default function AskPage() {
  return (
    <SetupReadinessGuard>
      <ChatInterface />
    </SetupReadinessGuard>
  );
}

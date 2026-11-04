import type { Metadata } from "next";
import { SchemaReadinessSection } from "@/components/SchemaReadinessSection";

export const metadata: Metadata = {
  title: "Data — AI for BI",
  description: "The catalogued tables, their columns and the business metrics the agent is grounded against.",
};

export default function DataPage() {
  return <SchemaReadinessSection />;
}

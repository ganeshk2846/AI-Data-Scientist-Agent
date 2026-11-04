import React from "react";
import { AppShell } from "@/components/AppShell";
import { IntroSequence } from "@/components/IntroSequence";

/**
 * The workspace layout: the rail, the header and the canvas, shared by all four
 * destinations. The setup and connection routes sit outside this group and keep
 * their own plain bar.
 */
export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <IntroSequence />
      <AppShell>{children}</AppShell>
    </>
  );
}

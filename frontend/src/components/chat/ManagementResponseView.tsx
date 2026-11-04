"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import { ExecutiveSection, ManagementResponse, MultiAgentWorkflowResult } from "@/types/api";
import { Markdown } from "@/components/ui/Markdown";
import { StatGroup, StatGroupBlock, StatItem, splitKpis } from "@/components/ui/Stat";
import {
  describeResult,
  firstSentence,
  isUnusableHeadline,
  scopeForValue,
} from "@/lib/narrative";

/**
 * The five sections the brief names, plus `impact_section`, which the backend
 * also sends and which is rendered on the same footing rather than dropped.
 */
const SECTION_ORDER: { key: keyof ManagementResponse; name: string }[] = [
  { key: "what", name: "What" },
  { key: "why", name: "Why" },
  { key: "so_what", name: "So what" },
  { key: "what_next", name: "What next" },
  { key: "scenario_section", name: "Scenario" },
  { key: "impact_section", name: "Impact" },
];

function isSection(value: unknown): value is ExecutiveSection {
  return typeof value === "object" && value !== null && "headline" in value;
}

/**
 * Disclaimers are the honesty of the product, so they are set at body size in
 * full ink inside their own well — never grey fine print, never truncated.
 */
function Disclaimers({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-2 rounded-card border border-[var(--border)] bg-raised px-3.5 py-3">
      {items.map((text, i) => (
        <p key={i} className="flex gap-2.5 text-body text-text">
          <AlertTriangle aria-hidden="true" className="mt-[0.2em] h-3.5 w-3.5 shrink-0 text-warning" />
          <span className="min-w-0 flex-1">{text}</span>
        </p>
      ))}
    </div>
  );
}

interface SectionProps {
  name: string;
  section: ExecutiveSection;
  headline: string;
  lead: boolean;
  /** Reading-order index, for the staggered arrival. */
  order: number;
  tiles: StatItem[];
  groups: { title: string; entries: ReturnType<typeof splitKpis>["groups"][number]["entries"] }[];
  /** The chart, placed inside the lead section when the result is a series. */
  chart?: React.ReactNode;
}

function Section({ name, section, headline, lead, order, tiles, groups, chart }: SectionProps) {
  const headingId = `section-${name.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <section
      aria-labelledby={headingId}
      className={clsx(
        "arrive border-l-2 pl-4",
        "sm:grid sm:grid-cols-[6.5rem_minmax(0,1fr)] sm:gap-x-7 sm:border-l-0 sm:pl-0",
        lead ? "border-accent" : "border-[var(--border)]"
      )}
      // Sections arrive in reading order, 55ms apart.
      style={{ animationDelay: `${order * 55}ms` }}
    >
      <h3
        id={headingId}
        className={clsx(
          "label-caps font-medium",
          "sm:border-l-2 sm:py-0.5 sm:pl-3",
          lead ? "text-accent sm:border-accent" : "text-muted sm:border-[var(--border)]"
        )}
      >
        {name}
      </h3>

      <div className="min-w-0">
        <p
          className={clsx(
            "text-balance font-semibold tracking-[-0.015em] text-text",
            // The answer's own statement is the biggest words on the screen
            // after the question: it is read from across a room.
            lead ? "text-[clamp(1.5rem,2.2vw,2rem)] leading-[1.12]" : "text-headline"
          )}
        >
          {headline}
        </p>

        {/* A series leads with its chart, not with one figure lifted out of it. */}
        {chart ? <div className="mt-4">{chart}</div> : null}

        {tiles.length > 0 ? (
          <div className="mt-4">
            <StatGroup items={tiles} leadFirst={lead && !chart} />
          </div>
        ) : null}

        {groups.length > 0 ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {groups.map((g) => (
              <StatGroupBlock key={g.title} title={g.title} entries={g.entries} />
            ))}
          </div>
        ) : null}

        {section.content ? <Markdown content={section.content} className="mt-4 max-w-prose-measure" /> : null}

        {section.disclaimers.length > 0 ? (
          <div className="mt-4 max-w-prose-measure">
            <Disclaimers items={section.disclaimers} />
          </div>
        ) : null}
      </div>
    </section>
  );
}

interface ManagementResponseViewProps {
  result: MultiAgentWorkflowResult;
  onRevealEvidence?: (figureLabel?: string) => void;
  evidenceLabel?: string;
  /** Rendered inside the lead section when the result is a series. */
  chart?: React.ReactNode;
}

/**
 * Renders only the sections that are present, in reading order.
 *
 * Two corrections to the backend's own text happen here, both presentation:
 * a headline that is a row count ("Query returned 12 rows.") is replaced by
 * the narrative's first real sentence or by a description of the result's
 * shape; and a KPI whose value is one row of a many-row result is labelled
 * with that row's own scope rather than reading as a total nobody computed.
 */
export function ManagementResponseView({
  result,
  onRevealEvidence,
  evidenceLabel,
  chart,
}: ManagementResponseViewProps) {
  const response = result.management_response;
  if (!response) return null;

  const present = SECTION_ORDER.map(({ key, name }) => ({
    name,
    section: (response as Record<string, unknown>)[key],
  })).filter((e): e is { name: string; section: ExecutiveSection } => isSection(e.section));

  if (present.length === 0) return null;

  const narrativeLead = firstSentence(result.composed_answer);

  return (
    <div className="space-y-12">
      {present.map(({ name, section }, i) => {
        const lead = i === 0;

        const headline = isUnusableHeadline(section.headline)
          ? (lead && narrativeLead) ||
            describeResult(result.query_result, result.chart_spec, section.headline || name)
          : section.headline;

        const { tiles, groups } = splitKpis(section.kpis ?? {});
        const scoped: StatItem[] = tiles.map((tile) => {
          const rowScope = scopeForValue(tile.raw, result.query_result);
          return {
            ...tile,
            // A figure that is one row of the result says which row it is,
            // instead of implying it is the whole.
            scope: rowScope ?? tile.scope ?? null,
            onReveal: onRevealEvidence ? () => onRevealEvidence(tile.label) : undefined,
            sourceLabel: evidenceLabel,
          };
        });

        return (
          <Section
            key={name}
            name={name}
            section={section}
            headline={headline}
            lead={lead}
            order={i}
            tiles={scoped}
            groups={groups}
            chart={lead ? chart : undefined}
          />
        );
      })}
    </div>
  );
}

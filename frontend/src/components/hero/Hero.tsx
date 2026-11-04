"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { ChartSpecification, QueryExecutionResult } from "@/types/api";
import { readToken, useTheme } from "@/lib/useTheme";
import { heroSeriesFrom } from "@/lib/heroSeries";
import { HeroPlot } from "./HeroPlot";
import { Disclosure } from "@/components/ui/Disclosure";
import { SqlBlock } from "@/components/ui/SqlBlock";

/**
 * three.js never reaches the first paint: it is imported only once the browser
 * has decided this device should run it, and never on the server.
 */
const HeroScene = dynamic(() => import("./HeroScene"), { ssr: false, loading: () => null });

/** True when this device and this viewer should get the WebGL field at all. */
function shouldRender3D(): boolean {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  // A coarse pointer means a phone or tablet: no pointer to track, and the GPU
  // and battery budget are not ours to spend.
  if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return false;
  if ((navigator.hardwareConcurrency ?? 8) < 4) return false;
  if (!window.matchMedia("(min-width: 1024px)").matches) return false;

  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

interface HeroProps {
  /** The opening answer's own rows: the series the scene is built from. */
  queryResult: QueryExecutionResult | null | undefined;
  chartSpec: ChartSpecification | null | undefined;
  /** The SQL that produced it, so the hero carries its own provenance. */
  sql?: string | null;
  title: string;
  subtitle: string;
  /** What is connected, named in real values. */
  scope?: string | null;
  /** Why there is no series yet, when there is none. */
  state?: "loading" | "error";
  /** What went wrong, in the backend's own words. */
  errorMessage?: string | null;
  onRetry?: () => void;
}

/**
 * The landing view's opening: the product's claim in display type beside the
 * warehouse's own numbers, rendered as a field of points that resolves into
 * the measure's curve.
 *
 * The scene is the data. Every point belongs to a row the opening query
 * returned; the axis, the ticks and the two labelled values are that result's
 * own, and the SQL that produced them is one disclosure away — so the hero
 * makes the product's argument rather than decorating it.
 */
export function Hero({ queryResult, chartSpec, sql, title, subtitle, scope, state, errorMessage, onRetry }: HeroProps) {
  const { theme } = useTheme();
  const [enabled, setEnabled] = useState(false);
  const [colors, setColors] = useState<{ accent: string; muted: string } | null>(null);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  // Re-read on a theme change: the field is lit by the live tokens, so gold
  // stays gold in both modes instead of being frozen at mount.
  useEffect(() => {
    if (!shouldRender3D()) return;
    setColors({
      accent: readToken("--accent", "#e3c178"),
      muted: readToken("--gold-muted", "#a88449"),
    });
    setEnabled(true);
  }, [theme]);

  const series = React.useMemo(() => heroSeriesFrom(queryResult, chartSpec), [queryResult, chartSpec]);
  const withField = enabled && colors !== null && series !== null;

  return (
    <section aria-labelledby="hero-title" className="hero-shell grain relative isolate overflow-hidden">
      <div className="relative z-10 grid items-center gap-8 px-6 py-12 sm:px-10 sm:py-16 lg:grid-cols-[minmax(0,0.84fr)_minmax(0,1.16fr)] lg:gap-10 lg:px-14 lg:py-20">
        <div className="min-w-0">
          <h1
            id="hero-title"
            className="font-display text-hero text-balance text-text"
          >
            {title}
          </h1>
          <p className="mt-6 max-w-[38ch] text-[clamp(1rem,1.2vw,1.125rem)] leading-relaxed text-muted">{subtitle}</p>

          {scope ? (
            <p className="mt-7 flex flex-wrap items-center gap-x-2.5 gap-y-1 font-mono text-label text-faint">
              {scope}
            </p>
          ) : null}

          {series ? (
            <div className="mt-8 max-w-[34rem]">
              <p className="text-label text-muted">
                <span className="text-text">{series.measure}</span>
                {series.range ? <span> · {series.range}</span> : null}
                <span className="text-faint">
                  {" "}
                  · {series.points.length} values, one point each · lowest{" "}
                  <span className="num-display" title={`Exact value: ${series.trough.exact}`}>
                    {series.trough.display}
                  </span>{" "}
                  in {series.trough.label}
                </span>
              </p>
              {sql ? (
                <Disclosure
                  label={<span className="text-label font-medium text-muted">The query behind this scene</span>}
                  className="mt-1"
                >
                  <SqlBlock sql={sql} label="the opening query" />
                </Disclosure>
              ) : null}
            </div>
          ) : null}
        </div>

        {/* The plane and the field share one coordinate space, so a label lands
            on the point it names. The field is behind, the plane in front. */}
        <div className="relative min-w-0">
          {series ? (
            <div className="relative h-[clamp(16rem,34vw,30rem)] w-full">
              {withField && colors ? (
                <HeroScene
                  points={series.points}
                  colors={colors}
                  /* Additive light reads as gold glowing out of a dark ground;
                     on paper it only washes the ink out, so light mode lays the
                     points down normally instead. */
                  blend={theme === "dark" ? "add" : "normal"}
                  activeIndex={activeIndex}
                  className="absolute inset-0 z-0"
                />
              ) : null}
              <HeroPlot
                series={series}
                activeIndex={activeIndex}
                onActiveChange={setActiveIndex}
                withField={withField}
                className="absolute inset-0 z-10 cursor-crosshair"
              />
            </div>
          ) : (
            /* No series yet. The opening query is one real model call, so the
               hero says which of the two things is true rather than drawing a
               shape that means nothing. */
            <div className="relative flex h-[clamp(14rem,30vw,26rem)] w-full items-end">
              {state === "error" ? (
                <div className="w-full">
                  <p className="text-body text-text">The opening query did not run.</p>
                  {errorMessage ? (
                    <p className="mt-1.5 max-w-prose-measure text-label text-muted">{errorMessage}</p>
                  ) : null}
                  {onRetry ? (
                    <button type="button" onClick={onRetry} className="link-gold mt-3 text-label">
                      Run it again
                    </button>
                  ) : null}
                </div>
              ) : (
                <div className="w-full space-y-3">
                  <span className="skeleton block h-px w-full" />
                  <div className="flex items-end gap-2">
                    {[0.42, 0.3, 0.55, 0.48, 0.5, 0.62, 0.78, 0.6, 0.72, 0.74, 0.92, 1].map((h, i) => (
                      <span key={i} className="skeleton block flex-1 rounded-none" style={{ height: `${h * 60}%` }} />
                    ))}
                  </div>
                  <p className="text-label text-faint">Running the opening query against the warehouse…</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

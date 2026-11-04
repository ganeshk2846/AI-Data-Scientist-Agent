"use client";

import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { clsx } from "clsx";
import { HeroSeries, PLOT, plotPercent, plotX, plotY } from "@/lib/heroSeries";

/**
 * The hero's plane: the axis, the ticks, the measure's own line, and the
 * labelled values.
 *
 * It is positioned in the same -1..1 space as the WebGL field behind it and
 * stretched with `preserveAspectRatio="none"`, exactly as the orthographic
 * camera stretches — so a label lands on the point it names at every size,
 * with no per-frame projection. Strokes carry `vector-effect` so the stretch
 * never thickens a rule.
 *
 * It renders with or without the canvas: under reduced motion, on a phone, on
 * a low-core machine or in a browser without WebGL this layer alone is the
 * hero, which is why it draws the series rather than only labelling it.
 */

const W = 1000;
const H = 560;

const sx = (x: number) => ((x + 1) / 2) * W;
const sy = (y: number) => ((1 - y) / 2) * H;

interface HeroPlotProps {
  series: HeroSeries;
  activeIndex: number | null;
  onActiveChange: (index: number | null) => void;
  /** True once the point field is running, so the plane can sit lighter on it. */
  withField: boolean;
  className?: string;
}

export function HeroPlot({ series, activeIndex, onActiveChange, withField, className }: HeroPlotProps) {
  const { points, peak } = series;

  const geometry = useMemo(() => {
    const coords = points.map((p, i) => ({ x: plotX(i, points.length), y: plotY(p.unit) }));
    const line = coords.map((c) => `${sx(c.x).toFixed(1)},${sy(c.y).toFixed(1)}`).join(" ");
    const area = `${sx(coords[0].x).toFixed(1)},${sy(PLOT.baseline).toFixed(1)} ${line} ${sx(
      coords[coords.length - 1].x
    ).toFixed(1)},${sy(PLOT.baseline).toFixed(1)}`;
    return { coords, line, area };
  }, [points]);

  /**
   * Pointer tracking, rAF-batched.
   *
   * `getBoundingClientRect()` inside the pointermove handler forces a layout
   * read on every event — a hundred a second, in the same frames the WebGL
   * field is drawing. The rect is read once per animation frame instead, and
   * only while the pointer is actually over the plane.
   */
  const frame = useRef<number | null>(null);
  const pending = useRef<{ x: number; node: HTMLDivElement } | null>(null);

  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    },
    []
  );

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      pending.current = { x: event.clientX, node: event.currentTarget };
      if (frame.current !== null) return;
      frame.current = requestAnimationFrame(() => {
        frame.current = null;
        const next = pending.current;
        if (!next) return;
        const rect = next.node.getBoundingClientRect();
        if (rect.width === 0) return;
        // The pointer picks the nearest row on the axis, in the plot's own space.
        const x = ((next.x - rect.left) / rect.width) * 2 - 1;
        const t = (x - PLOT.left) / (PLOT.right - PLOT.left);
        const index = Math.round(t * (points.length - 1));
        onActiveChange(index < 0 || index > points.length - 1 ? null : index);
      });
    },
    [onActiveChange, points.length]
  );

  const onPointerLeave = useCallback(() => {
    pending.current = null;
    onActiveChange(null);
  }, [onActiveChange]);

  const peakIndex = points.indexOf(peak);
  // The opening row, unless that is the peak — then the closing row.
  const openingIndex = peakIndex === 0 ? points.length - 1 : 0;

  const active = activeIndex !== null ? points[activeIndex] : null;
  const activeCoord = activeIndex !== null ? geometry.coords[activeIndex] : null;

  /** A labelled value: the figure, its row, and a hairline down to its point. */
  const ValueLabel = ({
    index,
    align,
    delayMs,
    tone,
  }: {
    index: number;
    align: "above" | "below";
    delayMs: number;
    tone: "peak" | "trough";
  }) => {
    const point = points[index];
    const coord = geometry.coords[index];
    const pos = plotPercent(coord.x, coord.y);
    // A label near an edge aligns to that edge instead of straddling it, so a
    // figure at the end of the series is never half outside the frame.
    const fraction = (coord.x + 1) / 2;
    const horizontal =
      fraction > 0.74 ? "-translate-x-full pr-1" : fraction < 0.26 ? "translate-x-0 pl-1" : "-translate-x-1/2";
    return (
      <div
        className={clsx(
          "hero-label absolute z-20",
          horizontal,
          align === "above" ? "-translate-y-full pb-3" : "pt-3"
        )}
        style={{ left: pos.left, top: pos.top, animationDelay: `${delayMs}ms` }}
      >
        <p
          className={clsx(
            "num-display whitespace-nowrap text-[22px] font-semibold leading-none tracking-[-0.02em] sm:text-[28px] lg:text-[34px]",
            tone === "peak" ? "gold-foil" : "text-text"
          )}
          title={`Exact value: ${point.exact}`}
        >
          {point.display}
        </p>
        <p className="mt-1.5 whitespace-nowrap text-label text-muted">{point.label}</p>
      </div>
    );
  };

  return (
    <div
      /* The caller positions this layer: it is absolute over the field in the
         hero, and in normal flow where there is no field. A hardcoded
         `relative` here beat the caller's `absolute` and collapsed it. */
      className={className}
      role="img"
      aria-label={series.description}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        aria-hidden="true"
        className="absolute inset-0 h-full w-full"
      >
        <defs>
          <linearGradient id="hero-axis" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" style={{ stopColor: "var(--gold-hairline)", stopOpacity: 0 }} />
            <stop offset="18%" style={{ stopColor: "var(--gold-hairline)", stopOpacity: 1 }} />
            <stop offset="82%" style={{ stopColor: "var(--gold-hairline)", stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: "var(--gold-hairline)", stopOpacity: 0 }} />
          </linearGradient>
          <linearGradient id="hero-area" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" style={{ stopColor: "var(--accent)", stopOpacity: withField ? 0.14 : 0.2 }} />
            <stop offset="100%" style={{ stopColor: "var(--accent)", stopOpacity: 0 }} />
          </linearGradient>
          <linearGradient id="hero-line" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" style={{ stopColor: "var(--gold-muted)" }} />
            <stop offset="55%" style={{ stopColor: "var(--accent)" }} />
            <stop offset="100%" style={{ stopColor: "var(--accent)" }} />
          </linearGradient>
        </defs>

        {/* The baseline: the one heavier rule, fading at both ends. */}
        <line
          x1={sx(PLOT.left - 0.08)}
          x2={sx(PLOT.right + 0.08)}
          y1={sy(PLOT.baseline)}
          y2={sy(PLOT.baseline)}
          style={{ stroke: "url(#hero-axis)" }}
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />

        {/* A shallow wash under the series, so the curve sits on a surface. */}
        <polygon points={geometry.area} style={{ fill: "url(#hero-area)" }} className="hero-area" />

        {/* The measure's own line, tracing left to right as the field lands. */}
        <polyline
          points={geometry.line}
          fill="none"
          strokeWidth={withField ? 1.5 : 2}
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
          pathLength={1}
          style={{ stroke: "url(#hero-line)", opacity: withField ? 0.5 : 1 }}
          className="hero-trace"
        />

        {/* The row the pointer is on: a vertical read-off, never a tooltip box. */}
        {activeCoord ? (
          <g className="hero-readout">
            <line
              x1={sx(activeCoord.x)}
              x2={sx(activeCoord.x)}
              y1={sy(activeCoord.y)}
              y2={sy(PLOT.baseline)}
              style={{ stroke: "var(--accent)", strokeOpacity: 0.5 }}
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
            <circle cx={sx(activeCoord.x)} cy={sy(activeCoord.y)} r={4} style={{ fill: "var(--accent)" }} />
          </g>
        ) : null}
      </svg>

      {/* Ticks and labels are DOM, not SVG: the plane is stretched, and
          stretched text is distorted text. */}
      <div className="absolute inset-0 z-10">
        {points.map((point, i) => {
          const pos = plotPercent(plotX(i, points.length), PLOT.baseline);
          const isActive = activeIndex === i;
          // On a narrow canvas every other tick is enough to read the axis.
          const sparse = points.length > 8 && i % 2 === 1;
          return (
            <span
              key={point.key}
              style={{ left: pos.left, top: pos.top, animationDelay: `${900 + i * 40}ms` }}
              className={clsx(
                "hero-label absolute -translate-x-1/2 translate-y-3 whitespace-nowrap text-label tracking-[0.06em]",
                isActive ? "text-accent" : "text-muted",
                sparse && "hidden lg:inline"
              )}
            >
              {point.tick}
            </span>
          );
        })}

        {/* Two values are labelled on the plane: where the series starts, and
            its highest row. Both sit above their own point, far enough apart
            that neither lands on the other's curve. The lowest row is named in
            the caption beside the plot rather than crowding the axis. */}
        <ValueLabel index={peakIndex} align="above" delayMs={1500} tone="peak" />
        {openingIndex !== peakIndex ? (
          <ValueLabel index={openingIndex} align="above" delayMs={1750} tone="trough" />
        ) : null}

        {active && activeCoord && activeIndex !== peakIndex && activeIndex !== openingIndex ? (
          <div
            className="absolute z-30 -translate-x-1/2 -translate-y-full pb-3"
            style={{ left: plotPercent(activeCoord.x, activeCoord.y).left, top: plotPercent(activeCoord.x, activeCoord.y).top }}
          >
            <p
              className="num-display whitespace-nowrap text-[22px] font-semibold leading-none text-text"
              title={`Exact value: ${active.exact}`}
            >
              {active.display}
            </p>
            <p className="mt-1 whitespace-nowrap text-label text-muted">{active.label}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

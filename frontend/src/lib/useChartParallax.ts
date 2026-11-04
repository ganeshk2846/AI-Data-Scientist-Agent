"use client";

import { RefObject, useCallback, useRef } from "react";

/**
 * Separates a plot's grid from its series as the pointer moves, so the chart
 * has depth between its own layers rather than reading as one flat picture.
 *
 * The two layers move by a few pixels in opposite directions. Both writes are
 * `transform` on the Plotly SVG groups themselves — composite-only, batched
 * into one animation frame, and never touching a parent whose custom
 * properties would recalculate every child.
 */
export function useChartParallax(containerRef: RefObject<HTMLDivElement | null>, depth = 6) {
  const frame = useRef<number | null>(null);
  const next = useRef<{ x: number; y: number } | null>(null);

  const apply = useCallback(() => {
    frame.current = null;
    const root = containerRef.current;
    const point = next.current;
    if (!root || !point) return;

    const rect = root.getBoundingClientRect();
    if (rect.width === 0) return;

    const dx = (point.x - rect.left) / rect.width - 0.5;
    const dy = (point.y - rect.top) / rect.height - 0.5;

    const grid = root.querySelector<SVGGElement>(".gridlayer");
    const series = root.querySelector<SVGGElement>(".plot");
    if (grid) grid.style.transform = `translate(${(-dx * depth).toFixed(2)}px, ${(-dy * depth * 0.5).toFixed(2)}px)`;
    if (series) series.style.transform = `translate(${(dx * depth * 0.6).toFixed(2)}px, ${(dy * depth * 0.3).toFixed(2)}px)`;
  }, [containerRef, depth]);

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      if (event.pointerType !== "mouse") return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      next.current = { x: event.clientX, y: event.clientY };
      if (frame.current === null) frame.current = requestAnimationFrame(apply);
    },
    [apply]
  );

  const onPointerLeave = useCallback(() => {
    if (frame.current !== null) {
      cancelAnimationFrame(frame.current);
      frame.current = null;
    }
    next.current = null;
    const root = containerRef.current;
    if (!root) return;
    for (const sel of [".gridlayer", ".plot"]) {
      const el = root.querySelector<SVGGElement>(sel);
      if (el) el.style.transform = "";
    }
  }, [containerRef]);

  return { onPointerMove, onPointerLeave };
}

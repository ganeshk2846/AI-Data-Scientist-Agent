"use client";

import { useCallback, useRef } from "react";

/**
 * A couple of degrees of pointer-tracked tilt, plus a highlight that follows
 * the pointer across the surface.
 *
 * Written against the frame budget: the handler only ever writes `transform`
 * and two custom properties on the element itself — never on a parent, which
 * would recalculate styles for every child — and the write is batched into one
 * animation frame, so a fast pointer cannot queue more work than the compositor
 * can take. Disabled outright for coarse pointers and reduced motion.
 */
export function useTilt(maxDegrees = 3) {
  const frame = useRef<number | null>(null);
  const node = useRef<HTMLElement | null>(null);
  const next = useRef<{ x: number; y: number } | null>(null);

  const apply = useCallback(() => {
    frame.current = null;
    const el = node.current;
    const point = next.current;
    if (!el || !point) return;

    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const px = (point.x - rect.left) / rect.width;
    const py = (point.y - rect.top) / rect.height;

    const rotateY = (px - 0.5) * 2 * maxDegrees;
    const rotateX = (0.5 - py) * 2 * maxDegrees;

    el.style.setProperty("--px", `${px * 100}%`);
    el.style.setProperty("--py", `${py * 100}%`);
    el.style.transform = `perspective(900px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg)`;
  }, [maxDegrees]);

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      if (event.pointerType !== "mouse") return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      node.current = event.currentTarget;
      next.current = { x: event.clientX, y: event.clientY };
      if (frame.current === null) frame.current = requestAnimationFrame(apply);
    },
    [apply]
  );

  const onPointerLeave = useCallback((event: React.PointerEvent<HTMLElement>) => {
    if (frame.current !== null) {
      cancelAnimationFrame(frame.current);
      frame.current = null;
    }
    next.current = null;
    event.currentTarget.style.transform = "";
  }, []);

  return { onPointerMove, onPointerLeave };
}

"use client";

import { RefObject, useEffect } from "react";

/**
 * Counts a figure up to its value as it arrives.
 *
 * Three rules make this safe on a product whose claim is that every number is
 * verified:
 *
 *  1. The element already contains the final figure when it mounts. The count
 *     only ever mutates text that is correct to begin with, so if script never
 *     runs the right number is on screen.
 *  2. The animation ALWAYS lands on `final` — the exact string the formatter
 *     produced from the API's own value. The last frame is assigned directly,
 *     never interpolated.
 *  3. Intermediate frames carry the target's own precision, so a whole count
 *     never flickers through a long fraction on its way up.
 *
 * It writes `textContent` on a ref rather than React state. Driving state from
 * `requestAnimationFrame` re-renders the component every frame — with four
 * figures on screen that is 240 renders a second, and the render alone blows
 * the frame budget. The DOM write touches one text node and nothing else.
 *
 * Under `prefers-reduced-motion` the figure simply stays at its value.
 */
export function useCountUp(
  ref: RefObject<HTMLElement | null>,
  target: number | null | undefined,
  final: string,
  format: (value: number) => string,
  durationMs = 850
): void {
  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    // The correct value is already rendered; make sure it stays that way.
    node.textContent = final;

    if (typeof target !== "number" || !Number.isFinite(target) || target === 0) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const decimals = (() => {
      const text = String(target);
      const dot = text.indexOf(".");
      return dot === -1 ? 0 : Math.min(text.length - dot - 1, 2);
    })();
    const factor = Math.pow(10, decimals);
    const quantise = (value: number) => Math.round(value * factor) / factor;

    let frame: number | null = null;
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min((now - start) / durationMs, 1);
      // Exponential ease-out: fast at first, settling softly.
      const eased = 1 - Math.pow(1 - t, 4);

      if (t >= 1) {
        node.textContent = final;
        frame = null;
        return;
      }

      node.textContent = format(quantise(target * eased));
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
      // Leave the true value behind, never a half-counted one.
      if (node.isConnected) node.textContent = final;
    };
  }, [ref, target, final, format, durationMs]);
}

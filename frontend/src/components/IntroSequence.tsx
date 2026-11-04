"use client";

import React, { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { readToken } from "@/lib/useTheme";

const IntroScene = dynamic(() => import("./hero/IntroScene"), { ssr: false, loading: () => null });

const PLAYED_KEY = "aibi-intro-played";
const WORDMARK = "AI for BI";

/** Where the rule under the wordmark sits, as a fraction of the viewport. */
const RULE_ANCHOR = 0.68;

/**
 * The opening sequence.
 *
 * Two seconds, once per session: the wordmark sets letter by letter, gold
 * sweeps across it, a line says what the product does, and a field of points
 * gathers into the rule beneath — then the rule releases upward, the overlay
 * lifts, and the app arrives behind it in reading order. The same material
 * that gathers here becomes the warehouse's own curve in the hero, so the
 * intro flows into the product rather than cutting to it.
 *
 * The app is mounted the whole time, not blocked by this: its queries — the
 * opening query above all, which is one real call to the model — are already
 * in flight while the sequence plays, so the two seconds are spent rather than
 * wasted.
 *
 * It is skipped entirely under `prefers-reduced-motion`, skipped once it has
 * played this session, and any key or click ends it immediately.
 */
export function IntroSequence() {
  const [phase, setPhase] = useState<"idle" | "playing" | "leaving" | "done">("idle");
  const [colors, setColors] = useState<{ accent: string; muted: string } | null>(null);
  const [withField, setWithField] = useState(false);
  const [skipHint, setSkipHint] = useState("Press any key to skip");

  const finish = useCallback(() => {
    setPhase((current) => (current === "playing" ? "leaving" : current));
  }, []);

  // What this browser should get, decided once. Nothing is written down and
  // no timer is started here: React re-runs mount effects in development, and
  // a sequence that recorded itself as played on the first of those runs would
  // never actually play.
  useEffect(() => {
    if (typeof window === "undefined") return;

    let played = false;
    try {
      played = sessionStorage.getItem(PLAYED_KEY) === "1";
    } catch {
      /* storage blocked — treat as not played; it is one sequence */
    }
    if (played || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPhase("done");
      return;
    }

    setColors({
      accent: readToken("--accent", "#e3c178"),
      muted: readToken("--gold-muted", "#a88449"),
    });

    // The field is held to the machines that can afford it, exactly as the
    // hero's is. Everything else still gets the wordmark and the sweep.
    // A phone has no key to press.
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) setSkipHint("Tap to skip");

    setWithField(
      window.matchMedia("(min-width: 768px)").matches &&
        (navigator.hardwareConcurrency ?? 8) >= 4 &&
        (() => {
          try {
            const canvas = document.createElement("canvas");
            return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
          } catch {
            return false;
          }
        })()
    );
    setPhase("playing");
  }, []);

  // While it plays: the page is held still and the sequence has two seconds.
  useEffect(() => {
    if (phase !== "playing") return;
    document.documentElement.setAttribute("data-intro", "running");
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const timer = setTimeout(finish, 2000);
    return () => {
      clearTimeout(timer);
      document.body.style.overflow = previousOverflow;
    };
  }, [phase, finish]);

  // Any key, any click: the sequence is a welcome, never a gate.
  useEffect(() => {
    if (phase !== "playing") return;
    const skip = () => finish();
    window.addEventListener("keydown", skip, { once: true });
    window.addEventListener("pointerdown", skip, { once: true });
    return () => {
      window.removeEventListener("keydown", skip);
      window.removeEventListener("pointerdown", skip);
    };
  }, [phase, finish]);

  // The app arrives in reading order the moment the overlay starts to lift,
  // and only now is the sequence recorded as played.
  useEffect(() => {
    if (phase !== "leaving") return;
    try {
      sessionStorage.setItem(PLAYED_KEY, "1");
    } catch {
      /* storage blocked — it will play once more next load, and no more */
    }
    document.documentElement.setAttribute("data-intro", "done");
    document.body.style.overflow = "";
    const timer = setTimeout(() => setPhase("done"), 620);
    return () => clearTimeout(timer);
  }, [phase]);

  if (phase === "idle" || phase === "done") return null;

  return (
    <div
      aria-hidden="true"
      data-leaving={phase === "leaving"}
      className="intro-overlay grain"
    >
      {withField && colors ? (
        <IntroScene
          colors={colors}
          release={phase === "leaving"}
          anchor={RULE_ANCHOR}
          className="intro-field"
        />
      ) : null}

      <div className="intro-stage">
        <p className="intro-wordmark font-display">
          {WORDMARK.split("").map((character, i) => (
            <span
              key={`${character}-${i}`}
              className="intro-letter"
              style={{ animationDelay: `${120 + i * 55}ms` }}
            >
              {character === " " ? " " : character}
            </span>
          ))}
          {/* The sweep is the wordmark again, clipped to its own glyphs, so
              the gold crosses the letters instead of a rectangle crossing the
              screen. */}
          <span aria-hidden="true" className="intro-sweep">
            {WORDMARK}
          </span>
        </p>
        <p className="intro-line">Every figure traced back to the query that produced it.</p>
      </div>

      {/* The rule the field gathers into — drawn, so it is there on a machine
          that never gets the canvas. */}
      <span aria-hidden="true" className="intro-rule rule-fade" />

      <p className="intro-skip">{skipHint}</p>
    </div>
  );
}

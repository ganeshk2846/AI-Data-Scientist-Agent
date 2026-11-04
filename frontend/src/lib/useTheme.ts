"use client";

import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "aibi-theme";

function currentTheme(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

/**
 * Reads and sets the active theme.
 *
 * The attribute on `<html>` is the single source of truth — it is set before
 * paint by the bootstrap script in layout.tsx, so there is no flash and no
 * hydration mismatch. Anything that needs to re-render on a theme change (the
 * chart, which has to re-read its colours) subscribes through the observer
 * rather than being told by a parent.
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    setThemeState(currentTheme());

    const observer = new MutationObserver(() => setThemeState(currentTheme()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    // Follow the OS only while the viewer has expressed no preference of their own.
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onMediaChange = (event: MediaQueryListEvent) => {
      try {
        if (localStorage.getItem(STORAGE_KEY)) return;
      } catch {
        /* storage blocked — follow the OS */
      }
      document.documentElement.setAttribute("data-theme", event.matches ? "dark" : "light");
    };
    media.addEventListener("change", onMediaChange);

    return () => {
      observer.disconnect();
      media.removeEventListener("change", onMediaChange);
    };
  }, []);

  const setTheme = useCallback((next: Theme) => {
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* storage blocked — the attribute still applies for this session */
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(currentTheme() === "dark" ? "light" : "dark");
  }, [setTheme]);

  return { theme, setTheme, toggleTheme };
}

/** Reads a design token off the document, so chart code never hard-codes a hex. */
export function readToken(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value.length > 0 ? value : fallback;
}

/**
 * A token as `rgba()` at a given alpha.
 *
 * Plotly writes colours straight into SVG `fill` attributes, where
 * `color-mix()` is not resolved and falls back to an opaque colour — which is
 * how a 16% wash under a line rendered as a solid gold block.
 */
export function readTokenRgba(name: string, alpha: number, fallback = "#000000"): string {
  const raw = readToken(name, fallback).trim();
  const hex = raw.startsWith("#") ? raw.slice(1) : raw;
  const full = hex.length === 3 ? hex.split("").map((c) => c + c).join("") : hex;
  if (full.length !== 6) return raw;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  if ([r, g, b].some(Number.isNaN)) return raw;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

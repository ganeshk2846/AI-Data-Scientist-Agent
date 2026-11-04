import type { Config } from "tailwindcss";

/**
 * Every colour resolves to a CSS custom property declared in src/app/globals.css,
 * so light and dark are two token sets rather than two Tailwind palettes, and no
 * component can hard-code a hex. See frontend/DESIGN.md.
 */
const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ground: "var(--ground)",
        surface: "var(--surface)",
        raised: "var(--raised)",
        active: "var(--active)",
        border: "var(--border)",
        rule: "var(--rule)",
        control: "var(--control)",
        text: "var(--text)",
        muted: "var(--muted)",
        faint: "var(--faint)",
        primary: "var(--primary)",
        "primary-ink": "var(--primary-ink)",
        positive: "var(--positive)",
        negative: "var(--negative)",
        warning: "var(--warning)",
        "pill-positive-bg": "var(--pill-positive-bg)",
        "pill-positive-ink": "var(--pill-positive-ink)",
        "pill-negative-bg": "var(--pill-negative-bg)",
        "pill-negative-ink": "var(--pill-negative-ink)",
        "pill-warning-bg": "var(--pill-warning-bg)",
        "pill-warning-ink": "var(--pill-warning-ink)",
        "pill-neutral-bg": "var(--pill-neutral-bg)",
        "pill-neutral-ink": "var(--pill-neutral-ink)",
        grid: "var(--grid)",
        sunken: "var(--sunken)",
        accent: "var(--accent)",
        "accent-ink": "var(--accent-ink)",
        "accent-soft": "var(--accent-soft)",
        "accent-edge": "var(--accent-edge)",
        "pill-accent-bg": "var(--pill-accent-bg)",
        "pill-accent-ink": "var(--pill-accent-ink)",
        "gold-muted": "var(--gold-muted)",
        "gold-hairline": "var(--gold-hairline)",
      },
      boxShadow: {
        raised: "var(--shadow-raised)",
        float: "var(--shadow-float)",
        lift: "var(--shadow-lift)",
      },
      fontFamily: {
        sans: ["Geist", "Inter", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "monospace"],
        // The display voice. One face, one weight, reserved for the places the
        // product speaks: the hero, the intro wordmark, a slide.
        display: ["Instrument Serif", "Iowan Old Style", "Palatino", "Georgia", "serif"],
      },
      fontSize: {
        // The scale from DESIGN.md §2. Five working sizes plus two figure sizes.
        micro: ["11px", { lineHeight: "1" }],
        label: ["12px", { lineHeight: "1.4" }],
        body: ["14px", { lineHeight: "1.55" }],
        section: ["16px", { lineHeight: "1.35" }],
        headline: ["20px", { lineHeight: "1.3" }],
        title: ["24px", { lineHeight: "1.25" }],
        "figure-sm": ["22px", { lineHeight: "1.1", letterSpacing: "-0.01em" }],
        figure: ["34px", { lineHeight: "1.0", letterSpacing: "-0.02em" }],
        // The focal point: one figure per answer is allowed to lead. Bigger
        // than it was, because this is read from the back of a room.
        display: ["clamp(3rem, 4.2vw, 4rem)", { lineHeight: "0.95", letterSpacing: "-0.03em" }],
        // The display voice, for a wordmark or a hero line.
        hero: ["clamp(3rem, 7.2vw, 5.5rem)", { lineHeight: "0.92", letterSpacing: "-0.025em" }],
        // Presentation mode only, where large type is the point.
        slide: ["clamp(2.5rem, 7vw, 5.5rem)", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
        "slide-sub": ["clamp(1.1rem, 2.2vw, 1.75rem)", { lineHeight: "1.35" }],
      },
      borderRadius: {
        card: "var(--radius-card)",
        control: "var(--radius-control)",
        chip: "var(--radius-chip)",
      },
      maxWidth: {
        thread: "var(--thread-max)",
        "prose-measure": "var(--prose-measure)",
      },
      transitionTimingFunction: {
        out: "var(--ease-out)",
        "in-out": "var(--ease-in-out)",
        drawer: "var(--ease-drawer)",
      },
    },
  },
  plugins: [],
};

export default config;

"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Moon, Settings, Sun } from "lucide-react";
import { clsx } from "clsx";
import { useTheme } from "@/lib/useTheme";
import { fetchReadiness } from "@/lib/api";
import { databaseName } from "@/lib/format";
import { DESTINATIONS, destinationForPath } from "@/lib/destinations";

/** The product's mark: drawn from its own subject — a figure and its evidence. */
export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="none">
      <rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 15.5V11m5 4.5V8m5 7.5v-3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={`Switch to the ${next} theme`}
      data-tooltip={`Switch to ${next}`}
      className="rail-item"
    >
      {theme === "dark" ? (
        <Sun aria-hidden="true" className="h-[18px] w-[18px]" />
      ) : (
        <Moon aria-hidden="true" className="h-[18px] w-[18px]" />
      )}
    </button>
  );
}

interface AppShellProps {
  children: React.ReactNode;
}

/**
 * The shell: an icon rail of four real routes, a header that names the scope,
 * and the canvas.
 *
 * Every destination is a `Link` to its own route rather than a state swap, so
 * the rail navigates with the browser alone — the failure mode where a broken
 * bundle leaves a screen full of controls that look alive and do nothing
 * cannot happen here. The active item is marked by ink brightness and a gold
 * rule, never a coloured pill.
 */
export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const active = destinationForPath(pathname);
  const { data } = useQuery({ queryKey: ["readiness"], queryFn: fetchReadiness, refetchInterval: 30_000 });

  const database = databaseName(data?.database?.path);
  const ready = data?.ready;

  return (
    <div className="min-h-screen bg-ground">
      <a href="#main" className="skip-link">
        Skip to content
      </a>

      {/* Rail — desktop */}
      <nav
        aria-label="Sections"
        className="fixed inset-y-0 left-0 z-40 hidden w-[var(--rail-width)] flex-col items-center border-r border-[var(--border)] bg-ground py-4 md:flex"
      >
        <Link href="/" aria-label="AI for BI — home" data-tooltip="AI for BI" className="rail-item rail-mark">
          <Mark className="h-[22px] w-[22px]" />
        </Link>

        <span aria-hidden="true" className="rule-fade my-4 h-px w-7" />

        <ul className="flex flex-1 flex-col items-center gap-1.5">
          {DESTINATIONS.map(({ key, href, label, hint, icon: Icon }) => {
            const isActive = active === key;
            return (
              <li key={key} className="relative">
                {isActive ? <span aria-hidden="true" className="rail-active-rule" /> : null}
                <Link
                  href={href}
                  aria-current={isActive ? "page" : undefined}
                  aria-label={`${label} — ${hint}`}
                  data-tooltip={label}
                  className={clsx("rail-item", isActive && "is-active")}
                >
                  <Icon aria-hidden="true" className="h-[18px] w-[18px]" />
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="flex flex-col items-center gap-1.5">
          <ThemeToggle />
          <Link href="/settings/connections" aria-label="Connections" data-tooltip="Connections" className="rail-item">
            <Settings aria-hidden="true" className="h-[18px] w-[18px]" />
          </Link>
        </div>
      </nav>

      {/* Header — names the product and the scope, so the screen is never anonymous */}
      <header className="sticky top-0 z-30 border-b border-[var(--border)] bg-ground/95 backdrop-blur-[2px] md:pl-[var(--rail-width)]">
        <div className="mx-auto flex h-14 max-w-[var(--canvas-max)] items-center justify-between gap-3 px-5 sm:px-8">
          <div className="flex min-w-0 items-center gap-2.5">
            <Link href="/" className="flex items-center gap-2 text-text md:hidden" aria-label="AI for BI — home">
              <Mark className="h-4 w-4 shrink-0" />
            </Link>
            <span className="truncate text-label font-semibold tracking-wide text-text">AI for BI</span>
            {database ? (
              <>
                <span aria-hidden="true" className="text-faint">
                  /
                </span>
                <span className="truncate font-mono text-label text-muted" title="The connected database">
                  {database}
                </span>
              </>
            ) : null}
          </div>

          <div className="flex shrink-0 items-center gap-3">
            {data?.llm?.model ? (
              <span className="hidden truncate font-mono text-label text-muted sm:inline" title="The active model">
                {data.llm.model}
              </span>
            ) : null}
            <span
              className="flex items-center gap-1.5 text-label text-muted"
              title={ready ? "Connected and ready" : "Not ready yet"}
            >
              <span
                aria-hidden="true"
                className={clsx("h-1.5 w-1.5 rounded-full", ready ? "bg-positive" : "bg-[var(--control)]")}
              />
              {ready ? "Ready" : "Connecting"}
            </span>
            <span className="md:hidden">
              <ThemeToggle />
            </span>
          </div>
        </div>
      </header>

      <main
        id="main"
        className="mx-auto max-w-[var(--canvas-max)] px-5 pb-32 pt-8 sm:px-8 md:pb-16 md:pl-[calc(var(--rail-width)+2rem)]"
      >
        {children}
      </main>

      {/* Bottom bar — phone */}
      <nav
        aria-label="Sections"
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-[var(--border)] bg-ground md:hidden"
      >
        {DESTINATIONS.map(({ key, href, label, hint, icon: Icon }) => {
          const isActive = active === key;
          return (
            <Link
              key={key}
              href={href}
              aria-current={isActive ? "page" : undefined}
              aria-label={`${label} — ${hint}`}
              className={clsx(
                "flex min-h-[56px] flex-1 flex-col items-center justify-center gap-1 py-2",
                "transition-colors duration-[120ms]",
                isActive ? "text-accent" : "text-muted"
              )}
            >
              <Icon aria-hidden="true" className="h-[18px] w-[18px]" />
              <span className="text-micro">{label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * `twMerge` classifies `text-*` by its built-in scale. Our type scale and our
 * colour tokens are both custom, so out of the box it cannot tell `text-label`
 * (a size) from `text-pill-neutral-ink` (a colour), treats them as the same
 * group, and silently drops one — which is why a status pill rendered at its
 * heading's size instead of 11px.
 *
 * Declaring the scale here fixes the classification for every component.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "micro",
            "label",
            "body",
            "section",
            "headline",
            "title",
            "figure",
            "figure-sm",
            "display",
            "hero",
            "slide",
            "slide-sub",
          ],
        },
      ],
    },
  },
});

/** Joins class names and resolves Tailwind conflicts with the scale above. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

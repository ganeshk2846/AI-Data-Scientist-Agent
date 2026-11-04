/**
 * The message a thrown value carries, if it carries one.
 *
 * A rejected mutation can throw anything, so narrowing beats asserting `any`:
 * an `Error` gives up its message, anything else falls back to wording the
 * caller chose for that specific failure.
 */
export function messageFrom(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim().length > 0) return error.message;
  if (typeof error === "string" && error.trim().length > 0) return error;
  return fallback;
}

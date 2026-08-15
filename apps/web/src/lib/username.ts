import { isReservedUsername } from "../data/reserved-usernames";

export type UsernameReason = "reserved" | "taken" | "ok" | "invalid";

export const USERNAME_MIN = 3;
export const USERNAME_MAX = 20;
export const USERNAME_RE = /^[a-z][a-z0-9_]{2,19}$/;

export function normalizeUsername(raw: string): string {
  return raw.trim().toLowerCase();
}

export function parseUsername(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const u = normalizeUsername(raw);
  if (u.length < USERNAME_MIN || u.length > USERNAME_MAX) return null;
  if (!USERNAME_RE.test(u)) return null;
  return u;
}

export function usernameFormatIssue(raw: string): "invalid" | "reserved" | null {
  const u = parseUsername(raw);
  if (!u) return "invalid";
  if (isReservedUsername(u)) return "reserved";
  return null;
}

export function reasonMessage(reason: UsernameReason): string {
  if (reason === "reserved") return "This name is reserved.";
  if (reason === "taken") return "Taken. Try another.";
  if (reason === "invalid") return "3–20 characters. Start with a letter. a–z, 0–9, underscore.";
  return "Available.";
}

export { isReservedUsername };

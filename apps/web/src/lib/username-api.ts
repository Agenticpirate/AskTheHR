import { isReservedUsername } from "../data/reserved-usernames";
import { parseUsername, type UsernameReason } from "./username";

export type UsernameCheck = {
  available: boolean;
  reason: UsernameReason;
};

export type UsernameClaimResult = {
  ok: boolean;
  username?: string;
  displayName?: string;
  claimedAt?: string;
  reason?: UsernameReason;
  source?: "kv" | "memory" | "preview";
};

const PREVIEW_KEY = "0pening.usernames.preview.v1";

type PreviewClaim = {
  username: string;
  displayName?: string;
  claimedAt: string;
};

function readPreview(): Record<string, PreviewClaim> {
  try {
    const raw = localStorage.getItem(PREVIEW_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    const out: Record<string, PreviewClaim> = {};
    for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
      if (!v || typeof v !== "object") continue;
      const o = v as Partial<PreviewClaim>;
      if (typeof o.username === "string" && typeof o.claimedAt === "string") {
        out[k] = {
          username: o.username,
          displayName: typeof o.displayName === "string" ? o.displayName : undefined,
          claimedAt: o.claimedAt,
        };
      }
    }
    return out;
  } catch {
    return {};
  }
}

function writePreview(claim: PreviewClaim): void {
  const next = readPreview();
  next[claim.username] = claim;
  localStorage.setItem(PREVIEW_KEY, JSON.stringify(next));
}

function asReason(value: unknown): UsernameReason | null {
  return value === "reserved" || value === "taken" || value === "ok" || value === "invalid"
    ? value
    : null;
}

export async function checkUsername(raw: string): Promise<UsernameCheck> {
  const parsed = parseUsername(raw);
  if (!parsed) return { available: false, reason: "invalid" };
  if (isReservedUsername(parsed)) return { available: false, reason: "reserved" };
  try {
    const res = await fetch(`/api/username?u=${encodeURIComponent(parsed)}`, {
      headers: { accept: "application/json" },
    });
    if (res.ok) {
      const data = (await res.json()) as { available?: unknown; reason?: unknown };
      const reason = asReason(data.reason);
      if (reason) {
        return { available: reason === "ok", reason };
      }
    }
  } catch {
    // fall through to local preview — Vite dev has no Pages Function
  }
  const preview = readPreview();
  if (preview[parsed]) return { available: false, reason: "taken" };
  return { available: true, reason: "ok" };
}

export async function claimUsernameRemote(
  username: string,
  displayName?: string,
): Promise<UsernameClaimResult> {
  const parsed = parseUsername(username);
  if (!parsed) return { ok: false, reason: "invalid" };
  if (isReservedUsername(parsed)) return { ok: false, reason: "reserved" };

  try {
    const res = await fetch("/api/username", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        username: parsed,
        displayName: displayName?.trim() || undefined,
      }),
    });
    const data = (await res.json()) as UsernameClaimResult;
    if (res.ok && data.ok && typeof data.username === "string") {
      writePreview({
        username: data.username,
        displayName: data.displayName,
        claimedAt: data.claimedAt || new Date().toISOString(),
      });
      return data;
    }
    const reason = asReason(data.reason);
    if (reason && reason !== "ok") return { ok: false, reason };
    if (res.status === 409) return { ok: false, reason: "taken" };
  } catch {
    // local preview fallback
  }

  const preview = readPreview();
  if (preview[parsed]) return { ok: false, reason: "taken" };
  const claimedAt = new Date().toISOString();
  const claim: PreviewClaim = {
    username: parsed,
    displayName: displayName?.trim() || undefined,
    claimedAt,
  };
  writePreview(claim);
  return { ok: true, username: parsed, displayName: claim.displayName, claimedAt, source: "preview" };
}

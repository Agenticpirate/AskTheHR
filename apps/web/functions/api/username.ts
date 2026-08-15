/**
 * Username availability + claim.
 * GET  /api/username?u=     → { available, reason: reserved|taken|ok|invalid }
 * POST /api/username        { username, displayName? }
 *
 * Uses KV binding USERNAMES when present. Otherwise an in-memory map
 * so the route never 500s (empty store, no invented users).
 * Reserved names always win over KV.
 */

import { isReservedUsername } from "../../src/data/reserved-usernames";
import { parseUsername, type UsernameReason } from "../../src/lib/username";

type Claim = {
  username: string;
  displayName?: string;
  claimedAt: string;
};

type Store = {
  claims: Record<string, Claim>;
  held: string[];
};

type KV = {
  get(key: string, type: "json"): Promise<unknown>;
  put(key: string, value: string): Promise<void>;
};

type Env = {
  USERNAMES?: KV;
};

type Ctx = {
  request: Request;
  env: Env;
};

const STORE_KEY = "claims";
const memory: Store = { claims: {}, held: [] };

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: jsonHeaders });
}

function cleanDisplayName(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const name = value.replace(/[\u0000-\u001f\u007f]/g, "").replace(/\s+/g, " ").trim();
  if (name.length < 1 || name.length > 32) return undefined;
  return name;
}

function emptyStore(): Store {
  return { claims: {}, held: [] };
}

function parseStore(raw: unknown): Store {
  const next = emptyStore();
  if (!raw || typeof raw !== "object") return next;
  const o = raw as Partial<Store>;
  if (o.claims && typeof o.claims === "object") {
    for (const [k, v] of Object.entries(o.claims)) {
      if (!v || typeof v !== "object") continue;
      const c = v as Partial<Claim>;
      const username = parseUsername(c.username ?? k);
      if (!username) continue;
      if (typeof c.claimedAt !== "string" || c.claimedAt.length < 8) continue;
      next.claims[username] = {
        username,
        displayName: cleanDisplayName(c.displayName),
        claimedAt: c.claimedAt,
      };
    }
  }
  if (Array.isArray(o.held)) {
    for (const h of o.held) {
      const u = parseUsername(h);
      if (u) next.held.push(u);
    }
  }
  return next;
}

function isHeld(store: Store, username: string): boolean {
  return store.held.includes(username);
}

function classify(store: Store, raw: unknown): { available: boolean; reason: UsernameReason; username?: string } {
  const username = parseUsername(raw);
  if (!username) return { available: false, reason: "invalid" };
  if (isReservedUsername(username) || isHeld(store, username)) {
    return { available: false, reason: "reserved", username };
  }
  if (store.claims[username]) return { available: false, reason: "taken", username };
  return { available: true, reason: "ok", username };
}

async function load(env: Env): Promise<{ store: Store; source: "kv" | "memory" }> {
  const kv = env.USERNAMES;
  if (kv) {
    try {
      const raw = await kv.get(STORE_KEY, "json");
      return { store: parseStore(raw), source: "kv" };
    } catch {
      // fall through to memory so the route never 500s
    }
  }
  return { store: { claims: { ...memory.claims }, held: [...memory.held] }, source: "memory" };
}

async function persist(env: Env, store: Store): Promise<"kv" | "memory"> {
  memory.claims = { ...store.claims };
  memory.held = [...store.held];
  const kv = env.USERNAMES;
  if (kv) {
    try {
      await kv.put(STORE_KEY, JSON.stringify(store));
      return "kv";
    } catch {
      // keep memory copy
    }
  }
  return "memory";
}

export async function onRequestGet(context: Ctx): Promise<Response> {
  const url = new URL(context.request.url);
  const { store } = await load(context.env);
  const result = classify(store, url.searchParams.get("u") ?? "");
  return json({ available: result.available, reason: result.reason });
}

export async function onRequestPost(context: Ctx): Promise<Response> {
  let body: unknown;
  try {
    body = await context.request.json();
  } catch {
    return json({ ok: false, reason: "invalid", available: false }, 400);
  }
  const o = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  const { store } = await load(context.env);
  const result = classify(store, o.username);
  if (result.reason !== "ok" || !result.username) {
    const status = result.reason === "taken" ? 409 : 400;
    return json({ ok: false, available: false, reason: result.reason }, status);
  }
  const claim: Claim = {
    username: result.username,
    displayName: cleanDisplayName(o.displayName),
    claimedAt: new Date().toISOString(),
  };
  store.claims[claim.username] = claim;
  const source = await persist(context.env, store);
  return json({ ok: true, ...claim, source });
}

export async function onRequestOptions(): Promise<Response> {
  return new Response(null, {
    status: 204,
    headers: {
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "content-type",
      "access-control-max-age": "86400",
    },
  });
}

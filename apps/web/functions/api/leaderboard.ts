/**
 * Public 0pening leaderboard.
 * GET    /api/leaderboard
 * POST   /api/leaderboard   {id, nickname, track, dailyStreak, weeklyStreak, xp, level}
 * DELETE /api/leaderboard?id=
 *
 * Uses KV binding LEADERBOARD when present. Otherwise an in-memory map
 * so the route never 500s (empty board, no invented users).
 */

type TrackId = "fresh" | "experienced";

type BoardEntry = {
  id: string;
  nickname: string;
  track: TrackId;
  dailyStreak: number;
  weeklyStreak: number;
  xp: number;
  level: string;
  publishedAt: string;
};

type KV = {
  get(key: string, type: "json"): Promise<unknown>;
  put(key: string, value: string): Promise<void>;
};

type Env = {
  LEADERBOARD?: KV;
};

type Ctx = {
  request: Request;
  env: Env;
};

const STORE_KEY = "entries";
const memory = new Map<string, BoardEntry>();

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: jsonHeaders });
}

function isTrack(value: unknown): value is TrackId {
  return value === "fresh" || value === "experienced";
}

function finiteInt(value: unknown, min: number, max: number): number | null {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  const i = Math.trunc(n);
  if (i < min || i > max) return null;
  return i;
}

function cleanNickname(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const nick = value.replace(/[\u0000-\u001f\u007f]/g, "").replace(/\s+/g, " ").trim();
  if (nick.length < 1 || nick.length > 32) return null;
  return nick;
}

function cleanId(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const id = value.trim();
  if (id.length < 8 || id.length > 80) return null;
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return null;
  return id;
}

function cleanLevel(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const level = value.replace(/[\u0000-\u001f\u007f]/g, "").trim();
  if (level.length < 1 || level.length > 40) return null;
  return level;
}

function parseEntry(raw: unknown): BoardEntry | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const id = cleanId(o.id);
  const nickname = cleanNickname(o.nickname);
  const track = o.track;
  const dailyStreak = finiteInt(o.dailyStreak, 0, 10_000);
  const weeklyStreak = finiteInt(o.weeklyStreak, 0, 10_000);
  const xp = finiteInt(o.xp, 0, 10_000_000);
  const level = cleanLevel(o.level);
  if (!id || !nickname || !isTrack(track) || dailyStreak === null || weeklyStreak === null || xp === null || !level) {
    return null;
  }
  const publishedAt =
    typeof o.publishedAt === "string" && o.publishedAt.length > 0 && o.publishedAt.length < 80
      ? o.publishedAt
      : new Date().toISOString();
  return { id, nickname, track, dailyStreak, weeklyStreak, xp, level, publishedAt };
}

function sortTop(rows: BoardEntry[]): BoardEntry[] {
  return [...rows]
    .sort((a, b) => {
      if (b.dailyStreak !== a.dailyStreak) return b.dailyStreak - a.dailyStreak;
      if (b.weeklyStreak !== a.weeklyStreak) return b.weeklyStreak - a.weeklyStreak;
      return b.xp - a.xp;
    })
    .slice(0, 50);
}

async function load(env: Env): Promise<{ entries: BoardEntry[]; source: "kv" | "memory" }> {
  const kv = env.LEADERBOARD;
  if (kv) {
    try {
      const raw = await kv.get(STORE_KEY, "json");
      const list = Array.isArray(raw) ? raw.map(parseEntry).filter((e): e is BoardEntry => e !== null) : [];
      return { entries: sortTop(list), source: "kv" };
    } catch {
      // fall through to memory so the route never 500s
    }
  }
  return { entries: sortTop([...memory.values()]), source: "memory" };
}

async function persist(env: Env, entries: BoardEntry[]): Promise<"kv" | "memory"> {
  const top = sortTop(entries);
  memory.clear();
  for (const row of top) memory.set(row.id, row);
  const kv = env.LEADERBOARD;
  if (kv) {
    try {
      await kv.put(STORE_KEY, JSON.stringify(top));
      return "kv";
    } catch {
      // keep memory copy
    }
  }
  return "memory";
}

export async function onRequestGet(context: Ctx): Promise<Response> {
  const { entries, source } = await load(context.env);
  return json({ entries, source });
}

export async function onRequestPost(context: Ctx): Promise<Response> {
  let body: unknown;
  try {
    body = await context.request.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }
  const entry = parseEntry(body);
  if (!entry) {
    return json({ error: "Invalid entry. Need id, nickname, track, dailyStreak, weeklyStreak, xp, level." }, 400);
  }
  const { entries } = await load(context.env);
  const next = [entry, ...entries.filter((e) => e.id !== entry.id)];
  const source = await persist(context.env, next);
  return json({ entry, source });
}

export async function onRequestDelete(context: Ctx): Promise<Response> {
  const url = new URL(context.request.url);
  const id = cleanId(url.searchParams.get("id"));
  if (!id) return json({ error: "Missing id" }, 400);
  const { entries } = await load(context.env);
  if (!entries.some((e) => e.id === id)) {
    return json({ ok: true, source: context.env.LEADERBOARD ? "kv" : "memory" }, 200);
  }
  const source = await persist(
    context.env,
    entries.filter((e) => e.id !== id),
  );
  return json({ ok: true, source });
}

export async function onRequestOptions(): Promise<Response> {
  return new Response(null, {
    status: 204,
    headers: {
      "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
      "access-control-allow-headers": "content-type",
      "access-control-max-age": "86400",
    },
  });
}

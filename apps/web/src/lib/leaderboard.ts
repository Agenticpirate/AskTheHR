import type { TrackId } from "./tracker";

export type BoardEntry = {
  id: string;
  nickname: string;
  track: TrackId;
  dailyStreak: number;
  weeklyStreak: number;
  xp: number;
  level: string;
  publishedAt: string;
};

export type BoardSource = "live" | "preview" | "empty" | "error";

export type BoardResult = {
  entries: BoardEntry[];
  source: BoardSource;
  message?: string;
};

const PREVIEW_KEY = "seeker.leaderboard.preview.v1";

function sortEntries(rows: BoardEntry[]): BoardEntry[] {
  return [...rows].sort((a, b) => {
    if (b.dailyStreak !== a.dailyStreak) return b.dailyStreak - a.dailyStreak;
    if (b.weeklyStreak !== a.weeklyStreak) return b.weeklyStreak - a.weeklyStreak;
    return b.xp - a.xp;
  }).slice(0, 50);
}

function readPreview(): BoardEntry[] {
  try {
    const raw = localStorage.getItem(PREVIEW_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return sortEntries(parsed.filter(isEntry));
  } catch {
    return [];
  }
}

function isEntry(value: unknown): value is BoardEntry {
  if (!value || typeof value !== "object") return false;
  const o = value as Partial<BoardEntry>;
  return (
    typeof o.id === "string" &&
    typeof o.nickname === "string" &&
    (o.track === "fresh" || o.track === "experienced") &&
    typeof o.dailyStreak === "number" &&
    typeof o.weeklyStreak === "number" &&
    typeof o.xp === "number" &&
    typeof o.level === "string"
  );
}

export function writePreview(entry: BoardEntry | null, publicId: string): void {
  const current = readPreview().filter((e) => e.id !== publicId);
  const next = entry ? sortEntries([entry, ...current]) : current;
  localStorage.setItem(PREVIEW_KEY, JSON.stringify(next));
}

export async function fetchBoard(): Promise<BoardResult> {
  try {
    const res = await fetch("/api/leaderboard", { headers: { accept: "application/json" } });
    if (res.ok) {
      const data = (await res.json()) as { entries?: unknown };
      const entries = Array.isArray(data.entries) ? sortEntries(data.entries.filter(isEntry)) : [];
      if (entries.length === 0) {
        return { entries: [], source: "empty", message: "Be the first streak." };
      }
      return { entries, source: "live" };
    }
  } catch {
    // fall through to preview
  }
  const preview = readPreview();
  if (preview.length > 0) {
    return {
      entries: preview,
      source: "preview",
      message: "Only you can see this until the board is live.",
    };
  }
  return {
    entries: [],
    source: "error",
    message: "The public board is not live yet. Publish from Me to keep a local preview.",
  };
}

export async function publishEntry(entry: BoardEntry): Promise<boolean> {
  writePreview(entry, entry.id);
  try {
    const res = await fetch("/api/leaderboard", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(entry),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function unpublishEntry(id: string): Promise<boolean> {
  writePreview(null, id);
  try {
    const res = await fetch(`/api/leaderboard?id=${encodeURIComponent(id)}`, { method: "DELETE" });
    return res.ok || res.status === 404;
  } catch {
    return false;
  }
}

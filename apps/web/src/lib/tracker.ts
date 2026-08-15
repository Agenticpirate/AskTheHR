import { addDays, startOfWeek, weekKey } from "./dates";

export type Application = {
  id: string;
  jobId?: string;
  title: string;
  company: string;
  url?: string;
  country?: string;
  appliedAt: string;
  note?: string;
};

export type Profile = {
  nickname: string;
  weeklyTarget: number;
  createdAt: string;
};

export type TrackerState = {
  profile: Profile;
  applications: Application[];
};

/** Swap this for a Cloudflare KV / D1 client once auth exists. */
export interface TrackerStore {
  get(): TrackerState;
  set(state: TrackerState): void;
}

const KEY = "seeker.tracker.v1";

function uid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `a_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function defaultState(): TrackerState {
  return {
    profile: {
      nickname: "",
      weeklyTarget: 8,
      createdAt: new Date().toISOString(),
    },
    applications: [],
  };
}

function revive(raw: unknown): TrackerState {
  const base = defaultState();
  if (!raw || typeof raw !== "object") return base;
  const o = raw as Partial<TrackerState>;
  const target = Number(o.profile?.weeklyTarget);
  return {
    profile: {
      nickname: String(o.profile?.nickname ?? ""),
      weeklyTarget: Number.isFinite(target) ? Math.min(40, Math.max(1, target)) : 8,
      createdAt: o.profile?.createdAt || base.profile.createdAt,
    },
    applications: Array.isArray(o.applications)
      ? o.applications.filter((a) => a && a.title && a.appliedAt)
      : [],
  };
}

export const localStore: TrackerStore = {
  get() {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? revive(JSON.parse(raw)) : defaultState();
    } catch {
      return defaultState();
    }
  },
  set(state) {
    localStorage.setItem(KEY, JSON.stringify(state));
  },
};

export function logApplication(
  state: TrackerState,
  input: Omit<Application, "id" | "appliedAt"> & { appliedAt?: string },
): TrackerState {
  if (input.jobId && state.applications.some((a) => a.jobId === input.jobId)) {
    return state;
  }
  const row: Application = {
    id: uid(),
    appliedAt: input.appliedAt || new Date().toISOString(),
    title: input.title,
    company: input.company,
    jobId: input.jobId,
    url: input.url,
    country: input.country,
    note: input.note,
  };
  return { ...state, applications: [row, ...state.applications] };
}

export function removeApplication(state: TrackerState, id: string): TrackerState {
  return { ...state, applications: state.applications.filter((a) => a.id !== id) };
}

export function weekCount(state: TrackerState, when = new Date()): number {
  const key = weekKey(when);
  return state.applications.filter((a) => weekKey(new Date(a.appliedAt)) === key).length;
}

export function computeStreak(state: TrackerState, when = new Date()): number {
  const target = state.profile.weeklyTarget;
  if (target <= 0 || state.applications.length === 0) return 0;
  const counts = new Map<string, number>();
  let earliest = when;
  for (const a of state.applications) {
    const d = new Date(a.appliedAt);
    if (Number.isNaN(d.getTime())) continue;
    const k = weekKey(d);
    counts.set(k, (counts.get(k) || 0) + 1);
    if (d < earliest) earliest = d;
  }
  let cursor = startOfWeek(when);
  if ((counts.get(weekKey(cursor)) || 0) < target) {
    cursor = addDays(cursor, -7);
  }
  const floor = startOfWeek(earliest);
  let streak = 0;
  while (cursor >= floor && streak < 52) {
    if ((counts.get(weekKey(cursor)) || 0) >= target) {
      streak += 1;
      cursor = addDays(cursor, -7);
    } else {
      break;
    }
  }
  return streak;
}

export function alreadyApplied(state: TrackerState, jobId: string): boolean {
  return state.applications.some((a) => a.jobId === jobId);
}

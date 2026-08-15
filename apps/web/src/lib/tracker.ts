import { addDays, dayKey, daysSince, formatLoggedTime, startOfWeek, weekKey } from "./dates";
import { isReservedUsername, parseUsername } from "./username";

export type AppStatus = "applied" | "followed_up" | "interview" | "offer" | "rejected";
export type TrackId = "fresh" | "experienced";
export type Track = TrackId | "";

export const APP_STATUSES: AppStatus[] = [
  "applied",
  "followed_up",
  "interview",
  "offer",
  "rejected",
];

export const STATUS_LABEL: Record<AppStatus, string> = {
  applied: "Applied",
  followed_up: "Followed up",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

export type Application = {
  id: string;
  jobId?: string;
  title: string;
  company: string;
  url?: string;
  country?: string;
  appliedAt: string;
  note?: string;
  status?: AppStatus;
};

export type Plan = "free" | "paid";

export type WhatsAppPrefs = {
  optedIn: boolean;
  phone: string;
  enabled: boolean;
};

export type ReminderPrefs = {
  enabled: boolean;
  time: string;
  timezone: string;
  lastFired?: string;
};

export type Profile = {
  nickname: string;
  username?: string;
  usernameClaimedAt?: string;
  usernameReclaimed?: boolean;
  email?: string;
  track: Track;
  weeklyTarget: number;
  dailyMinutes: number;
  dailyApps: number;
  dailySkillMinutes: number;
  dailyOutreach: number;
  createdAt: string;
  plan: Plan;
  whatsapp: WhatsAppPrefs;
  reminder: ReminderPrefs;
};

export type DayLog = {
  minutes: number;
  skillMinutes: number;
  skillNote?: string;
  outreach: number;
  checkedIn: boolean;
  skillAdds?: number;
};

export type TrackerState = {
  profile: Profile;
  applications: Application[];
  days: Record<string, DayLog>;
  xp: number;
  badges: string[];
  badgeUnlocks: Record<string, string>;
  publicId: string;
  published: boolean;
};

export type TrackPreset = {
  id: TrackId;
  label: string;
  blurb: string;
  dailyMinutes: number;
  dailyApps: number;
  dailySkillMinutes: number;
  dailyOutreach: number;
  weeklyTarget: number;
};

export const TRACKS: Record<TrackId, TrackPreset> = {
  fresh: {
    id: "fresh",
    label: "Fresh",
    blurb: "Entry or career switch. Usually a full-time search — cap the day at about four quality hours.",
    dailyMinutes: 180,
    dailyApps: 4,
    dailySkillMinutes: 45,
    dailyOutreach: 1,
    weeklyTarget: 20,
  },
  experienced: {
    id: "experienced",
    label: "Experienced",
    blurb: "Mid or senior, often employed. One to two focused hours. Quality over spray.",
    dailyMinutes: 90,
    dailyApps: 2,
    dailySkillMinutes: 30,
    dailyOutreach: 2,
    weeklyTarget: 10,
  },
};

export const LEVELS = [
  { name: "Seeker", min: 0 },
  { name: "Focused", min: 100 },
  { name: "Relentless", min: 300 },
  { name: "Closer", min: 700 },
  { name: "Offer-ready", min: 1500 },
] as const;

export type LevelInfo = {
  name: string;
  min: number;
  next: number | null;
  progress: number;
};

export function levelFor(xp: number): LevelInfo {
  let current: (typeof LEVELS)[number] = LEVELS[0];
  for (const level of LEVELS) {
    if (xp >= level.min) current = level;
  }
  const idx = LEVELS.findIndex((l) => l.name === current.name);
  const nxt = idx >= 0 && idx < LEVELS.length - 1 ? LEVELS[idx + 1] : null;
  const span = nxt ? nxt.min - current.min : 1;
  const progress = nxt ? Math.min(100, Math.round(((xp - current.min) / span) * 100)) : 100;
  return { name: current.name, min: current.min, next: nxt ? nxt.min : null, progress };
}

export const BADGE_META: Record<string, { label: string; hint: string }> = {
  "first-apply": { label: "First apply", hint: "Logged the first application" },
  "daily-7": { label: "7-day streak", hint: "Seven consecutive active days" },
  "daily-30": { label: "30-day streak", hint: "Thirty consecutive active days" },
  "week-7-checkins": { label: "Full week", hint: "Seven check-ins in a week" },
  "week-hit": { label: "Week hit", hint: "Hit a weekly application target" },
  "apps-50": { label: "50 applications", hint: "Fifty tailored applications logged" },
  "skill-week": { label: "Skill week", hint: "Five days with skill work in a week" },
  shared: { label: "Broadcast", hint: "Shared a progress card" },
};

export const BADGE_ORDER = [
  "first-apply",
  "daily-7",
  "daily-30",
  "week-7-checkins",
  "week-hit",
  "skill-week",
  "apps-50",
  "shared",
] as const;

export type RingId = "minutes" | "apps" | "skill" | "outreach";

export type RingView = {
  id: RingId;
  label: string;
  value: number;
  max: number;
  hit: boolean;
  unit: string;
};

/** Swap this for a Cloudflare KV / D1 client once auth exists. */
export interface TrackerStore {
  get(): TrackerState;
  set(state: TrackerState): void;
}

const KEY_V1 = "seeker.tracker.v1";
const KEY_V2 = "seeker.tracker.v2";

function uid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `a_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function newPublicId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `p_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function emptyDay(): DayLog {
  return { minutes: 0, skillMinutes: 0, outreach: 0, checkedIn: false };
}

export function defaultWhatsApp(): WhatsAppPrefs {
  return { optedIn: false, phone: "", enabled: false };
}

export function defaultReminder(): ReminderPrefs {
  return { enabled: false, time: "09:00", timezone: "Asia/Calcutta" };
}

function reviveWhatsApp(raw: unknown): WhatsAppPrefs {
  const base = defaultWhatsApp();
  if (!raw || typeof raw !== "object") return base;
  const o = raw as Partial<WhatsAppPrefs>;
  return {
    optedIn: Boolean(o.optedIn),
    phone: typeof o.phone === "string" ? o.phone.trim().slice(0, 24) : "",
    enabled: Boolean(o.enabled),
  };
}

function reviveReminder(raw: unknown): ReminderPrefs {
  const base = defaultReminder();
  if (!raw || typeof raw !== "object") return base;
  const o = raw as Partial<ReminderPrefs>;
  const time = typeof o.time === "string" ? o.time : base.time;
  const m = /^(\d{1,2}):(\d{2})/.exec(time.trim());
  const norm = m
    ? `${String(Math.min(23, Math.max(0, Number(m[1])))).padStart(2, "0")}:${String(Math.min(59, Math.max(0, Number(m[2])))).padStart(2, "0")}`
    : base.time;
  return {
    enabled: Boolean(o.enabled),
    time: norm,
    timezone: typeof o.timezone === "string" && o.timezone.trim() ? o.timezone.trim() : base.timezone,
    lastFired: typeof o.lastFired === "string" && /^\d{4}-\d{2}-\d{2}$/.test(o.lastFired) ? o.lastFired : undefined,
  };
}

function reviveUnlocks(raw: unknown): Record<string, string> {
  if (!raw || typeof raw !== "object") return {};
  const next: Record<string, string> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof k === "string" && typeof v === "string") next[k] = v;
  }
  return next;
}

export function defaultState(): TrackerState {
  return {
    profile: {
      nickname: "",
      track: "",
      weeklyTarget: 8,
      dailyMinutes: 0,
      dailyApps: 0,
      dailySkillMinutes: 0,
      dailyOutreach: 0,
      createdAt: new Date().toISOString(),
      plan: "free",
      whatsapp: defaultWhatsApp(),
      reminder: defaultReminder(),
    },
    applications: [],
    days: {},
    xp: 0,
    badges: [],
    badgeUnlocks: {},
    publicId: newPublicId(),
    published: false,
  };
}

function clampTarget(n: number, fallback: number): number {
  if (!Number.isFinite(n)) return fallback;
  return Math.min(40, Math.max(1, n));
}

function asStatus(value: unknown): AppStatus | undefined {
  if (typeof value !== "string") return undefined;
  return (APP_STATUSES as string[]).includes(value) ? (value as AppStatus) : undefined;
}

function reviveApplication(raw: unknown): Application | null {
  if (!raw || typeof raw !== "object") return null;
  const a = raw as Partial<Application>;
  if (!a.title || !a.appliedAt) return null;
  return {
    id: String(a.id || uid()),
    jobId: a.jobId,
    title: String(a.title),
    company: String(a.company || "Unlisted company"),
    url: a.url,
    country: a.country,
    appliedAt: String(a.appliedAt),
    note: a.note,
    status: asStatus(a.status) ?? "applied",
  };
}

function reviveDay(raw: unknown): DayLog {
  if (!raw || typeof raw !== "object") return emptyDay();
  const d = raw as Partial<DayLog>;
  const minutes = Number(d.minutes);
  const skillMinutes = Number(d.skillMinutes);
  const outreach = Number(d.outreach);
  const skillAdds = Number(d.skillAdds);
  return {
    minutes: Number.isFinite(minutes) ? Math.max(0, minutes) : 0,
    skillMinutes: Number.isFinite(skillMinutes) ? Math.max(0, skillMinutes) : 0,
    skillNote: typeof d.skillNote === "string" ? d.skillNote : undefined,
    outreach: Number.isFinite(outreach) ? Math.max(0, outreach) : 0,
    checkedIn: Boolean(d.checkedIn),
    skillAdds: Number.isFinite(skillAdds) && skillAdds > 0 ? skillAdds : undefined,
  };
}

function applyTrack(profile: Profile, track: TrackId): Profile {
  const preset = TRACKS[track];
  return {
    ...profile,
    track,
    weeklyTarget: preset.weeklyTarget,
    dailyMinutes: preset.dailyMinutes,
    dailyApps: preset.dailyApps,
    dailySkillMinutes: preset.dailySkillMinutes,
    dailyOutreach: preset.dailyOutreach,
  };
}

function revive(raw: unknown): TrackerState {
  const base = defaultState();
  if (!raw || typeof raw !== "object") return base;
  const o = raw as Partial<TrackerState>;
  const trackRaw = o.profile?.track;
  const track: Track = trackRaw === "fresh" || trackRaw === "experienced" ? trackRaw : "";
  const plan: Plan = o.profile?.plan === "paid" ? "paid" : "free";
  let whatsapp = reviveWhatsApp(o.profile?.whatsapp);
  if (plan !== "paid") whatsapp = { ...whatsapp, enabled: false };
  const claimed = parseUsername(o.profile?.username ?? "") ?? undefined;
  const reservedNow = Boolean(claimed && isReservedUsername(claimed));
  let profile: Profile = {
    nickname: String(o.profile?.nickname ?? ""),
    username: reservedNow ? undefined : claimed,
    usernameClaimedAt:
      typeof o.profile?.usernameClaimedAt === "string" && o.profile.usernameClaimedAt.length > 8
        ? o.profile.usernameClaimedAt
        : undefined,
    usernameReclaimed: Boolean(o.profile?.usernameReclaimed) || reservedNow,
    email: typeof o.profile?.email === "string" && o.profile.email.trim()
      ? o.profile.email.trim().slice(0, 120)
      : undefined,
    track,
    weeklyTarget: clampTarget(Number(o.profile?.weeklyTarget), 8),
    dailyMinutes: Number(o.profile?.dailyMinutes) || 0,
    dailyApps: Number(o.profile?.dailyApps) || 0,
    dailySkillMinutes: Number(o.profile?.dailySkillMinutes) || 0,
    dailyOutreach: Number(o.profile?.dailyOutreach) || 0,
    createdAt: o.profile?.createdAt || base.profile.createdAt,
    plan,
    whatsapp,
    reminder: reviveReminder(o.profile?.reminder),
  };
  if (track && (profile.dailyMinutes <= 0 || profile.dailyApps <= 0)) {
    const preset = TRACKS[track];
    profile = {
      ...profile,
      dailyMinutes: preset.dailyMinutes,
      dailyApps: preset.dailyApps,
      dailySkillMinutes: preset.dailySkillMinutes,
      dailyOutreach: preset.dailyOutreach,
    };
  }
  const days: Record<string, DayLog> = {};
  if (o.days && typeof o.days === "object") {
    for (const [k, v] of Object.entries(o.days)) {
      if (/^\d{4}-\d{2}-\d{2}$/.test(k)) days[k] = reviveDay(v);
    }
  }
  const applications = Array.isArray(o.applications)
    ? o.applications.map(reviveApplication).filter((a): a is Application => a !== null)
    : [];
  const badges = Array.isArray(o.badges) ? o.badges.filter((b): b is string => typeof b === "string") : [];
  const publicId = typeof o.publicId === "string" && o.publicId.length >= 8 ? o.publicId : newPublicId();
  return finalize({
    profile,
    applications,
    days,
    xp: 0,
    badges,
    badgeUnlocks: reviveUnlocks(o.badgeUnlocks),
    publicId,
    published: Boolean(o.published),
  });
}

function migrateV1(raw: unknown): TrackerState {
  const base = defaultState();
  if (!raw || typeof raw !== "object") return base;
  const o = raw as { profile?: Partial<Profile>; applications?: unknown[] };
  const applications = Array.isArray(o.applications)
    ? o.applications.map(reviveApplication).filter((a): a is Application => a !== null)
    : [];
  return finalize({
    profile: {
      nickname: String(o.profile?.nickname ?? ""),
      track: "",
      weeklyTarget: clampTarget(Number(o.profile?.weeklyTarget), 8),
      dailyMinutes: 0,
      dailyApps: 0,
      dailySkillMinutes: 0,
      dailyOutreach: 0,
      createdAt: o.profile?.createdAt || base.profile.createdAt,
      plan: "free",
      whatsapp: defaultWhatsApp(),
      reminder: defaultReminder(),
    },
    applications,
    days: {},
    xp: 0,
    badges: [],
    badgeUnlocks: {},
    publicId: newPublicId(),
    published: false,
  });
}

export function appsOnDay(state: TrackerState, date: string): number {
  return state.applications.filter((a) => dayKey(new Date(a.appliedAt)) === date).length;
}

export function todayRings(state: TrackerState, when = new Date()): RingView[] {
  const date = dayKey(when);
  const day = state.days[date] ?? emptyDay();
  const fallback = TRACKS.fresh;
  const maxM = state.profile.dailyMinutes || fallback.dailyMinutes;
  const maxA = state.profile.dailyApps || fallback.dailyApps;
  const maxS = state.profile.dailySkillMinutes || fallback.dailySkillMinutes;
  const maxO = state.profile.dailyOutreach || fallback.dailyOutreach;
  const apps = appsOnDay(state, date);
  return [
    { id: "minutes", label: "Time", value: day.minutes, max: maxM, hit: day.minutes >= maxM, unit: "min" },
    { id: "apps", label: "Applications", value: apps, max: maxA, hit: apps >= maxA, unit: "" },
    { id: "skill", label: "Skills", value: day.skillMinutes, max: maxS, hit: day.skillMinutes >= maxS, unit: "min" },
    { id: "outreach", label: "Outreach", value: day.outreach, max: maxO, hit: day.outreach >= maxO, unit: "" },
  ];
}

export function ringsHitCount(state: TrackerState, when = new Date()): number {
  if (!state.profile.track) return 0;
  return todayRings(state, when).filter((r) => r.hit).length;
}

export function isDailyWin(state: TrackerState, date: string): boolean {
  if (!state.profile.track) return false;
  const when = new Date(`${date}T12:00:00`);
  return todayRings(state, when).every((r) => r.hit);
}

function dayHasActivity(state: TrackerState, date: string): boolean {
  const day = state.days[date];
  if (day && (day.checkedIn || day.minutes > 0 || day.skillMinutes > 0 || day.outreach > 0)) {
    return true;
  }
  return appsOnDay(state, date) > 0;
}

export function computeDailyStreak(state: TrackerState, when = new Date()): number {
  let cursor = dayKey(when);
  if (!dayHasActivity(state, cursor)) {
    cursor = dayKey(addDays(when, -1));
  }
  let streak = 0;
  for (let i = 0; i < 400; i += 1) {
    if (!dayHasActivity(state, cursor)) break;
    streak += 1;
    const d = new Date(`${cursor}T12:00:00`);
    cursor = dayKey(addDays(d, -1));
  }
  return streak;
}

function weeksTouched(state: TrackerState): string[] {
  const keys = new Set<string>();
  for (const a of state.applications) {
    const d = new Date(a.appliedAt);
    if (!Number.isNaN(d.getTime())) keys.add(weekKey(d));
  }
  for (const date of Object.keys(state.days)) {
    const d = new Date(`${date}T12:00:00`);
    if (!Number.isNaN(d.getTime())) keys.add(weekKey(d));
  }
  return [...keys];
}

function weekDates(key: string): string[] {
  const [y, m, d] = key.split("-").map(Number);
  const start = new Date(y, m - 1, d);
  return Array.from({ length: 7 }, (_, i) => dayKey(addDays(start, i)));
}

function hasWeekHit(state: TrackerState): boolean {
  const target = state.profile.weeklyTarget;
  if (target <= 0) return false;
  const counts = new Map<string, number>();
  for (const a of state.applications) {
    const d = new Date(a.appliedAt);
    if (Number.isNaN(d.getTime())) continue;
    const k = weekKey(d);
    counts.set(k, (counts.get(k) || 0) + 1);
  }
  for (const n of counts.values()) {
    if (n >= target) return true;
  }
  return false;
}

function countWeeklyHits(state: TrackerState): number {
  const target = state.profile.weeklyTarget;
  if (target <= 0) return 0;
  const counts = new Map<string, number>();
  for (const a of state.applications) {
    const d = new Date(a.appliedAt);
    if (Number.isNaN(d.getTime())) continue;
    const k = weekKey(d);
    counts.set(k, (counts.get(k) || 0) + 1);
  }
  let n = 0;
  for (const c of counts.values()) {
    if (c >= target) n += 1;
  }
  return n;
}

function hasWeek7Checkins(state: TrackerState): boolean {
  for (const key of weeksTouched(state)) {
    const n = weekDates(key).filter((date) => state.days[date]?.checkedIn).length;
    if (n >= 7) return true;
  }
  const thisWeek = weekDates(weekKey(new Date())).filter((date) => state.days[date]?.checkedIn).length;
  return thisWeek >= 7;
}

function hasSkillWeek(state: TrackerState): boolean {
  const keys = new Set(weeksTouched(state));
  keys.add(weekKey(new Date()));
  for (const key of keys) {
    const n = weekDates(key).filter((date) => (state.days[date]?.skillMinutes ?? 0) > 0).length;
    if (n >= 5) return true;
  }
  return false;
}

export function computeXp(state: TrackerState): number {
  let xp = state.applications.length * 10;
  for (const [date, day] of Object.entries(state.days)) {
    xp += Math.floor(day.minutes / 15) * 3;
    const sessions = day.skillAdds ?? (day.skillMinutes > 0 ? 1 : 0);
    xp += sessions * 8;
    xp += day.outreach * 6;
    if (day.checkedIn) xp += 5;
    if (isDailyWin(state, date)) xp += 25;
  }
  xp += countWeeklyHits(state) * 50;
  return xp;
}

export function computeBadges(state: TrackerState): string[] {
  const next = new Set(state.badges);
  if (state.applications.length >= 1) next.add("first-apply");
  if (state.applications.length >= 50) next.add("apps-50");
  if (hasWeekHit(state)) next.add("week-hit");
  if (hasWeek7Checkins(state)) next.add("week-7-checkins");
  if (hasSkillWeek(state)) next.add("skill-week");
  const daily = computeDailyStreak(state);
  if (daily >= 7) next.add("daily-7");
  if (daily >= 30) next.add("daily-30");
  return [...next];
}

function stampUnlocks(prev: Record<string, string> | undefined, badges: string[]): Record<string, string> {
  const next = { ...(prev ?? {}) };
  const now = new Date().toISOString();
  for (const id of badges) {
    if (!next[id]) next[id] = now;
  }
  return next;
}

function finalize(state: TrackerState): TrackerState {
  const badges = computeBadges(state);
  return {
    ...state,
    xp: computeXp(state),
    badges,
    badgeUnlocks: stampUnlocks(state.badgeUnlocks, badges),
  };
}

export function recentUnlocks(state: TrackerState, n = 4): { id: string; at: string }[] {
  return Object.entries(state.badgeUnlocks ?? {})
    .filter(([id]) => state.badges.includes(id))
    .sort((a, b) => (a[1] < b[1] ? 1 : -1))
    .slice(0, n)
    .map(([id, at]) => ({ id, at }));
}

export const localStore: TrackerStore = {
  get() {
    try {
      const v2 = localStorage.getItem(KEY_V2);
      if (v2) return revive(JSON.parse(v2));
      const v1 = localStorage.getItem(KEY_V1);
      if (v1) {
        const migrated = migrateV1(JSON.parse(v1));
        localStorage.setItem(KEY_V2, JSON.stringify(migrated));
        return migrated;
      }
      return defaultState();
    } catch {
      return defaultState();
    }
  },
  set(state) {
    localStorage.setItem(KEY_V2, JSON.stringify(state));
  },
};

export function logApplication(
  state: TrackerState,
  input: Omit<Application, "id" | "appliedAt"> & { appliedAt?: string; status?: AppStatus },
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
    status: input.status ?? "applied",
  };
  return finalize({ ...state, applications: [row, ...state.applications] });
}

export function removeApplication(state: TrackerState, id: string): TrackerState {
  return finalize({ ...state, applications: state.applications.filter((a) => a.id !== id) });
}

export function setApplicationStatus(state: TrackerState, id: string, status: AppStatus): TrackerState {
  return finalize({
    ...state,
    applications: state.applications.map((a) => (a.id === id ? { ...a, status } : a)),
  });
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

function patchDay(state: TrackerState, date: string, fn: (day: DayLog) => DayLog): TrackerState {
  const current = state.days[date] ?? emptyDay();
  return finalize({
    ...state,
    days: { ...state.days, [date]: fn(current) },
  });
}

export function addMinutes(state: TrackerState, amount = 15, when = new Date()): TrackerState {
  return patchDay(state, dayKey(when), (d) => ({ ...d, minutes: d.minutes + amount }));
}

export function addOutreach(state: TrackerState, amount = 1, when = new Date()): TrackerState {
  return patchDay(state, dayKey(when), (d) => ({ ...d, outreach: Math.max(0, d.outreach + amount) }));
}

export function addSkill(
  state: TrackerState,
  minutes = 15,
  note?: string,
  when = new Date(),
): TrackerState {
  return patchDay(state, dayKey(when), (d) => ({
    ...d,
    skillMinutes: d.skillMinutes + minutes,
    skillNote: note !== undefined ? note : d.skillNote,
    skillAdds: (d.skillAdds ?? 0) + 1,
  }));
}

export function setSkillNote(state: TrackerState, note: string, when = new Date()): TrackerState {
  return patchDay(state, dayKey(when), (d) => ({ ...d, skillNote: note }));
}

export function checkIn(state: TrackerState, when = new Date()): TrackerState {
  return patchDay(state, dayKey(when), (d) => ({ ...d, checkedIn: true }));
}

export function setTrack(state: TrackerState, track: TrackId): TrackerState {
  return finalize({
    ...state,
    profile: applyTrack(state.profile, track),
  });
}

export function setNickname(state: TrackerState, nickname: string): TrackerState {
  return { ...state, profile: { ...state.profile, nickname } };
}

export function claimUsername(
  state: TrackerState,
  username: string,
  opts?: { displayName?: string; email?: string },
): TrackerState {
  const parsed = parseUsername(username);
  if (!parsed || isReservedUsername(parsed)) return state;
  const display =
    typeof opts?.displayName === "string"
      ? opts.displayName.replace(/[\u0000-\u001f\u007f]/g, "").replace(/\s+/g, " ").trim().slice(0, 32)
      : "";
  const email =
    typeof opts?.email === "string" ? opts.email.trim().slice(0, 120) : "";
  const nickname = state.profile.nickname.trim() || display || parsed;
  return {
    ...state,
    profile: {
      ...state.profile,
      username: parsed,
      usernameClaimedAt: new Date().toISOString(),
      usernameReclaimed: false,
      nickname,
      email: email || state.profile.email,
    },
  };
}

export function markUsernameReclaimed(state: TrackerState): TrackerState {
  if (state.profile.usernameReclaimed && !state.profile.username) return state;
  return {
    ...state,
    profile: {
      ...state.profile,
      username: undefined,
      usernameReclaimed: true,
    },
  };
}

export function setWeeklyTarget(state: TrackerState, weeklyTarget: number): TrackerState {
  return finalize({
    ...state,
    profile: {
      ...state.profile,
      weeklyTarget: clampTarget(weeklyTarget, state.profile.weeklyTarget),
    },
  });
}

export function setPublished(state: TrackerState, published: boolean): TrackerState {
  return { ...state, published };
}

export function setPlan(state: TrackerState, plan: Plan): TrackerState {
  const whatsapp =
    plan === "paid" ? state.profile.whatsapp : { ...state.profile.whatsapp, enabled: false };
  return { ...state, profile: { ...state.profile, plan, whatsapp } };
}

export function setWhatsApp(state: TrackerState, patch: Partial<WhatsAppPrefs>): TrackerState {
  const next = { ...state.profile.whatsapp, ...patch };
  if (state.profile.plan !== "paid") next.enabled = false;
  return { ...state, profile: { ...state.profile, whatsapp: next } };
}

export function setReminder(state: TrackerState, patch: Partial<ReminderPrefs>): TrackerState {
  const next = { ...state.profile.reminder, ...patch };
  if (typeof patch.time === "string") {
    const m = /^(\d{1,2}):(\d{2})/.exec(patch.time.trim());
    next.time = m
      ? `${String(Math.min(23, Math.max(0, Number(m[1])))).padStart(2, "0")}:${String(Math.min(59, Math.max(0, Number(m[2])))).padStart(2, "0")}`
      : state.profile.reminder.time;
  }
  if (typeof patch.timezone === "string" && !patch.timezone.trim()) {
    next.timezone = "Asia/Calcutta";
  }
  return { ...state, profile: { ...state.profile, reminder: next } };
}

export function markReminderFired(state: TrackerState, date: string): TrackerState {
  return {
    ...state,
    profile: {
      ...state.profile,
      reminder: { ...state.profile.reminder, lastFired: date },
    },
  };
}

export function markShared(state: TrackerState): TrackerState {
  if (state.badges.includes("shared")) return state;
  return finalize({ ...state, badges: [...state.badges, "shared"] });
}

export function activityScore(state: TrackerState, date: string): number {
  const day = state.days[date];
  const apps = appsOnDay(state, date);
  return (day?.minutes ?? 0) + apps + (day?.skillMinutes ?? 0);
}

export function shareLine(state: TrackerState, when = new Date()): string {
  const day = daysSince(state.profile.createdAt, when);
  const track = state.profile.track ? TRACKS[state.profile.track].label : "Untracked";
  const rings = todayRings(state, when);
  const apps = rings.find((r) => r.id === "apps");
  const mins = state.days[dayKey(when)]?.minutes ?? 0;
  const time = mins >= 60 ? `${Math.round(mins / 60)}h` : `${mins}m`;
  const streak = computeDailyStreak(state, when);
  const level = levelFor(state.xp).name;
  const appBit = apps ? `${apps.value}/${apps.max} apps` : "0 apps";
  return `0pening · Day ${day} · ${track} · ${appBit} · ${time} · streak ${streak} · ${level}`;
}

export function dayNumber(state: TrackerState, when = new Date()): number {
  return daysSince(state.profile.createdAt, when);
}

export { formatLoggedTime };

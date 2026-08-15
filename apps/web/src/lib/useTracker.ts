import { useCallback, useEffect, useMemo, useState } from "react";
import {
  addMinutes,
  addOutreach,
  addSkill,
  alreadyApplied,
  checkIn,
  computeDailyStreak,
  computeStreak,
  defaultState,
  levelFor,
  localStore,
  logApplication,
  markReminderFired,
  markShared,
  recentUnlocks,
  removeApplication,
  ringsHitCount,
  setApplicationStatus,
  setNickname as writeNickname,
  setPlan,
  setReminder,
  setSkillNote,
  setTrack,
  setPublished,
  setWeeklyTarget,
  setWhatsApp,
  shareLine,
  todayRings,
  weekCount,
  type Application,
  type AppStatus,
  type Plan,
  type ReminderPrefs,
  type TrackId,
  type TrackerState,
  type WhatsAppPrefs,
} from "./tracker";

const EVT = "seeker-tracker";

export function useTracker() {
  const [state, setState] = useState<TrackerState>(() =>
    typeof localStorage === "undefined" ? defaultState() : localStore.get(),
  );

  useEffect(() => {
    const sync = () => setState(localStore.get());
    window.addEventListener("storage", sync);
    window.addEventListener(EVT, sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener(EVT, sync);
    };
  }, []);

  const commit = useCallback((next: TrackerState) => {
    localStore.set(next);
    setState(next);
    window.dispatchEvent(new Event(EVT));
  }, []);

  const thisWeek = weekCount(state);
  const streak = useMemo(() => computeStreak(state), [state]);
  const dailyStreak = useMemo(() => computeDailyStreak(state), [state]);
  const rings = useMemo(() => todayRings(state), [state]);
  const ringsHit = ringsHitCount(state);
  const level = useMemo(() => levelFor(state.xp), [state.xp]);
  const unlocks = useMemo(() => recentUnlocks(state), [state]);
  const todayKey = useMemo(() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }, [state]);
  const todayLog = state.days[todayKey] ?? {
    minutes: 0,
    skillMinutes: 0,
    outreach: 0,
    checkedIn: false,
  };

  return {
    state,
    thisWeek,
    streak,
    dailyStreak,
    target: state.profile.weeklyTarget,
    nickname: state.profile.nickname,
    track: state.profile.track,
    profile: state.profile,
    plan: state.profile.plan,
    whatsapp: state.profile.whatsapp,
    reminder: state.profile.reminder,
    xp: state.xp,
    level,
    badges: state.badges,
    unlocks,
    rings,
    ringsHit,
    today: todayLog,
    publicId: state.publicId,
    published: state.published,
    shareText: shareLine(state),
    setNickname: (nickname: string) => commit(writeNickname(state, nickname)),
    setTarget: (weeklyTarget: number) => commit(setWeeklyTarget(state, weeklyTarget)),
    setTrack: (track: TrackId) => commit(setTrack(state, track)),
    setPlan: (plan: Plan) => commit(setPlan(state, plan)),
    setWhatsApp: (patch: Partial<WhatsAppPrefs>) => commit(setWhatsApp(state, patch)),
    setReminder: (patch: Partial<ReminderPrefs>) => commit(setReminder(state, patch)),
    markReminderFired: (date: string) => commit(markReminderFired(state, date)),
    log: (input: Omit<Application, "id" | "appliedAt"> & { appliedAt?: string }) =>
      commit(logApplication(state, input)),
    remove: (id: string) => commit(removeApplication(state, id)),
    setStatus: (id: string, status: AppStatus) => commit(setApplicationStatus(state, id, status)),
    applied: (jobId: string) => alreadyApplied(state, jobId),
    addMinutes: (amount = 15) => commit(addMinutes(state, amount)),
    addOutreach: (amount = 1) => commit(addOutreach(state, amount)),
    addSkill: (minutes = 15, note?: string) => commit(addSkill(state, minutes, note)),
    setSkillNote: (note: string) => commit(setSkillNote(state, note)),
    checkIn: () => commit(checkIn(state)),
    markShared: () => commit(markShared(state)),
    setPublished: (published: boolean) => commit(setPublished(state, published)),
  };
}

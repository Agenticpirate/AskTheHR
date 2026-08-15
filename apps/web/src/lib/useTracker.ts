import { useCallback, useEffect, useMemo, useState } from "react";
import {
  alreadyApplied,
  computeStreak,
  localStore,
  logApplication,
  removeApplication,
  weekCount,
  type Application,
  type TrackerState,
} from "./tracker";

const EVT = "seeker-tracker";

export function useTracker() {
  const [state, setState] = useState<TrackerState>(() =>
    typeof localStorage === "undefined" ? {
      profile: { nickname: "", weeklyTarget: 8, createdAt: new Date().toISOString() },
      applications: [],
    } : localStore.get(),
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

  return {
    state,
    thisWeek,
    streak,
    target: state.profile.weeklyTarget,
    nickname: state.profile.nickname,
    setNickname: (nickname: string) =>
      commit({ ...state, profile: { ...state.profile, nickname } }),
    setTarget: (weeklyTarget: number) =>
      commit({
        ...state,
        profile: {
          ...state.profile,
          weeklyTarget: Math.min(40, Math.max(1, weeklyTarget)),
        },
      }),
    log: (input: Omit<Application, "id" | "appliedAt"> & { appliedAt?: string }) =>
      commit(logApplication(state, input)),
    remove: (id: string) => commit(removeApplication(state, id)),
    applied: (jobId: string) => alreadyApplied(state, jobId),
  };
}

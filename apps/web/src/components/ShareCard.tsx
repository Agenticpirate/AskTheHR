import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { dayNumber, TRACKS, type TrackerState } from "@/lib/tracker";
import { dayKey, formatLoggedTime } from "@/lib/dates";
import { CountUp } from "./CountUp";

export function ShareCard({
  state,
  text,
  dailyStreak,
  onCopied,
}: {
  state: TrackerState;
  text: string;
  dailyStreak: number;
  onCopied: () => void;
}) {
  const reduce = useReducedMotion();
  const [pop, setPop] = useState(0);
  const [copied, setCopied] = useState(false);
  const track = state.profile.track ? TRACKS[state.profile.track].label : "Untracked";
  const todayMins = state.days[dayKey()]?.minutes ?? 0;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setPop((n) => n + 1);
      onCopied();
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  return (
    <motion.div
      key={pop}
      animate={reduce || pop === 0 ? undefined : { scale: [1, 1.02, 1] }}
      transition={{ type: "spring", stiffness: 420, damping: 16 }}
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-card px-4 py-3 ring-1 ring-border"
    >
      <div className="min-w-0">
        <div className="micro text-primary">Cadence</div>
        <div className="mt-1 text-sm tracking-tight">
          Day {dayNumber(state)} · {track}
        </div>
        <div className="mt-1 flex flex-wrap gap-x-3 font-mono text-[11px] tabular-nums text-muted-foreground">
          <span>
            <CountUp value={dailyStreak} /> streak
          </span>
          <span>{formatLoggedTime(todayMins)}</span>
          <span>{state.xp} XP</span>
        </div>
      </div>
      <Button type="button" size="sm" onClick={() => void copy()}>
        {copied ? "Copied" : "Copy progress"}
      </Button>
    </motion.div>
  );
}

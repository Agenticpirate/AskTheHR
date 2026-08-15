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
    <div className="grid gap-4">
      <motion.div
        key={pop}
        animate={reduce || pop === 0 ? undefined : { scale: [1, 1.035, 1] }}
        transition={{ type: "spring", stiffness: 420, damping: 16 }}
        className="rounded-lg bg-card px-6 py-8 ring-1 ring-border"
      >
        <div className="micro text-primary">0pening</div>
        <div className="mt-3 font-heading text-3xl tracking-tight">
          Day {dayNumber(state)}
        </div>
        <div className="mt-1 text-sm text-muted-foreground">{track}</div>
        <div className="mt-6 grid grid-cols-3 gap-3 font-mono text-sm tabular-nums">
          <div>
            <CountUp value={dailyStreak} className="text-xl" />
            <div className="micro mt-1">Streak</div>
          </div>
          <div>
            <div className="text-xl">{formatLoggedTime(todayMins)}</div>
            <div className="micro mt-1">Time</div>
          </div>
          <div>
            <div className="text-xl">{state.xp}</div>
            <div className="micro mt-1">XP</div>
          </div>
        </div>
        <p className="mt-6 font-mono text-xs leading-relaxed text-muted-foreground">{text}</p>
      </motion.div>
      <Button type="button" onClick={() => void copy()}>
        {copied ? "Copied" : "Copy progress"}
      </Button>
    </div>
  );
}

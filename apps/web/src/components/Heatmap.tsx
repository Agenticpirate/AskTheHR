import { motion, useReducedMotion } from "motion/react";
import { lastNDays } from "@/lib/dates";
import { activityScore, type TrackerState } from "@/lib/tracker";
import { itemRise, staggerFast } from "@/lib/motion";

function tone(score: number): string {
  if (score <= 0) return "bg-white/5";
  if (score < 30) return "bg-primary/25";
  if (score < 90) return "bg-primary/50";
  if (score < 180) return "bg-primary/75";
  return "bg-primary";
}

export function Heatmap({ state }: { state: TrackerState }) {
  const reduce = useReducedMotion();
  const days = lastNDays(30);
  return (
    <div>
      <div className="micro mb-3">30-day heat</div>
      <motion.div
        className="grid grid-cols-10 gap-1.5"
        initial={reduce ? "show" : "hidden"}
        animate="show"
        variants={staggerFast}
      >
        {days.map((key) => {
          const score = activityScore(state, key);
          return (
            <motion.div
              key={key}
              title={`${key} · ${score}`}
              variants={itemRise}
              className={`aspect-square rounded-[3px] ${tone(score)}`}
            />
          );
        })}
      </motion.div>
    </div>
  );
}

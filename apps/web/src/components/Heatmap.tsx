import { motion, useReducedMotion } from "motion/react";
import { lastNDays } from "@/lib/dates";
import { activityScore, type TrackerState } from "@/lib/tracker";
import { cellPop, staggerHeat } from "@/lib/motion";

function tone(score: number): string {
  if (score <= 0) return "bg-foreground/10";
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
      <div className="micro mb-2">30-day heat</div>
      <motion.div
        className="grid gap-1"
        style={{ gridTemplateColumns: "repeat(15, minmax(0, 1fr))" }}
        initial={reduce ? "show" : "hidden"}
        animate="show"
        variants={staggerHeat}
      >
        {days.map((key) => {
          const score = activityScore(state, key);
          return (
            <motion.div
              key={key}
              title={`${key} · ${score}`}
              variants={cellPop}
              className={`aspect-square rounded-[2px] ${tone(score)}`}
            />
          );
        })}
      </motion.div>
    </div>
  );
}

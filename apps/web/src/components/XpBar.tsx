import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import type { LevelInfo } from "@/lib/tracker";
import { CountUp } from "./CountUp";

export function XpBar({ xp, level }: { xp: number; level: LevelInfo }) {
  const reduce = useReducedMotion();
  const fill = useRef<HTMLDivElement>(null);
  const flash = useRef<HTMLDivElement>(null);
  const prevLevel = useRef(level.name);

  useGSAP(() => {
    const el = fill.current;
    if (!el) return;
    if (reduce) {
      gsap.set(el, { width: `${level.progress}%` });
      return;
    }
    gsap.to(el, { width: `${level.progress}%`, duration: 0.4, ease: "power2.out" });
  }, [level.progress, reduce]);

  useEffect(() => {
    if (prevLevel.current === level.name) return;
    prevLevel.current = level.name;
    const el = flash.current;
    if (!el) return;
    if (reduce) return;
    gsap.fromTo(
      el,
      { opacity: 0.7 },
      { opacity: 0, duration: 0.32, ease: "power2.out" },
    );
  }, [level.name, reduce]);

  return (
    <div className="relative min-w-0">
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <div className="text-sm font-medium">{level.name}</div>
        <div className="font-mono text-xs tabular-nums text-muted-foreground">
          <CountUp value={xp} duration={0.4} />
          {level.next !== null ? ` / ${level.next}` : " XP"}
        </div>
      </div>
      <div className="relative h-1.5 overflow-hidden rounded-full bg-foreground/10">
        <div
          ref={fill}
          className="h-full rounded-full bg-primary"
          style={{ width: `${level.progress}%` }}
        />
        <div
          ref={flash}
          className="pointer-events-none absolute inset-0 bg-white opacity-0"
        />
      </div>
    </div>
  );
}

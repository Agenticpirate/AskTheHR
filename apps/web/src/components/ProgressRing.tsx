import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { motion, useReducedMotion } from "motion/react";
import { useRef } from "react";
import { CountUp } from "./CountUp";

export function ProgressRing({
  value,
  max,
  label,
  unit,
  hit,
  onClick,
  size = 148,
  compact = false,
}: {
  value: number;
  max: number;
  label: string;
  unit?: string;
  hit: boolean;
  onClick?: () => void;
  size?: number;
  compact?: boolean;
}) {
  const reduce = useReducedMotion();
  const circleRef = useRef<SVGCircleElement>(null);
  const r = compact ? 34 : 52;
  const c = 2 * Math.PI * r;
  const pct = max <= 0 ? 0 : Math.min(1, value / max);
  const dim = compact ? 88 : size;
  const center = dim / 2;

  useGSAP(() => {
    const el = circleRef.current;
    if (!el) return;
    const target = c * (1 - pct);
    if (reduce) {
      gsap.set(el, { strokeDashoffset: target });
      return;
    }
    gsap.to(el, {
      strokeDashoffset: target,
      duration: 0.9,
      ease: "power2.out",
    });
  }, [pct, c, reduce]);

  const inner = (
    <>
      <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} className="block">
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke="#3a3a3f"
          strokeWidth={compact ? 5 : 7}
        />
        <circle
          ref={circleRef}
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={hit ? "#0070f3" : "#ffffff"}
          strokeWidth={compact ? 5 : 7}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c}
          transform={`rotate(-90 ${center} ${center})`}
        />
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <CountUp
          value={value}
          className={`font-mono tabular-nums ${compact ? "text-lg" : "text-2xl"} tracking-tight`}
        />
        <div className="text-[10px] text-muted-foreground">
          / {max}
          {unit ? ` ${unit}` : ""}
        </div>
      </div>
    </>
  );

  if (onClick) {
    return (
      <motion.button
        type="button"
        onClick={onClick}
        whileHover={reduce ? undefined : { y: -2, filter: "brightness(1.08)" }}
        whileTap={reduce ? undefined : { scale: 0.98 }}
        className="group relative flex flex-col items-center gap-2"
      >
        <div className="relative">{inner}</div>
        <div className="micro">{label}</div>
      </motion.button>
    );
  }

  return (
    <div className="relative flex flex-col items-center gap-2">
      <div className="relative">{inner}</div>
      <div className="micro">{label}</div>
    </div>
  );
}

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useReducedMotion } from "motion/react";
import { useRef } from "react";
import type { RingView } from "@/lib/tracker";
import { ProgressRing } from "./ProgressRing";

export function TodayRings({
  rings,
  onAdjust,
  compact = false,
}: {
  rings: RingView[];
  onAdjust?: (id: RingView["id"]) => void;
  compact?: boolean;
}) {
  const reduce = useReducedMotion();
  const wrap = useRef<HTMLDivElement>(null);
  const hit = rings.length > 0 && rings.every((r) => r.hit);

  useGSAP(() => {
    const el = wrap.current;
    if (!el) return;
    if (!hit) {
      gsap.set(el, { boxShadow: "0 0 0 0 rgba(0,112,243,0)", scale: 1 });
      return;
    }
    if (reduce) {
      gsap.set(el, { boxShadow: "0 0 0 1px #0070f3", scale: 1 });
      return;
    }
    const tl = gsap.timeline();
    tl.fromTo(
      el,
      { scale: 1, boxShadow: "0 0 0 0 rgba(0,112,243,0)" },
      {
        scale: 1.03,
        boxShadow: "0 0 36px 0 rgba(0,112,243,0.45)",
        duration: 0.28,
        ease: "power2.out",
      },
    ).to(el, {
      scale: 1,
      boxShadow: "0 0 0 1px rgba(0,112,243,0.7)",
      duration: 0.45,
      ease: "power2.inOut",
    });
  }, [hit, reduce]);

  return (
    <div
      ref={wrap}
      className={`rounded-lg ring-1 ring-border ${compact ? "px-3 py-4" : "px-4 py-6 md:px-8 md:py-8"}`}
    >
      <div className={`grid grid-cols-2 ${compact ? "gap-3 sm:grid-cols-4" : "gap-6 sm:grid-cols-4"}`}>
        {rings.map((ring) => (
          <ProgressRing
            key={ring.id}
            value={ring.value}
            max={ring.max}
            label={ring.label}
            unit={ring.unit}
            hit={ring.hit}
            compact={compact}
            onClick={
              onAdjust && ring.id !== "apps"
                ? () => onAdjust(ring.id)
                : undefined
            }
          />
        ))}
      </div>
      {hit ? (
        <p className="micro mt-5 text-center text-primary">Daily complete</p>
      ) : null}
    </div>
  );
}

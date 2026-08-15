import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useReducedMotion } from "motion/react";
import { useRef } from "react";

export function CountUp({
  value,
  className,
  duration = 0.8,
}: {
  value: number;
  className?: string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduce = useReducedMotion();

  useGSAP(() => {
    const el = ref.current;
    if (!el) return;
    if (reduce) {
      el.textContent = String(Math.round(value));
      return;
    }
    const obj = { n: Number(el.textContent) || 0 };
    gsap.to(obj, {
      n: value,
      duration,
      ease: "power2.out",
      onUpdate: () => {
        el.textContent = String(Math.round(obj.n));
      },
    });
  }, [value, reduce, duration]);

  return (
    <span ref={ref} className={className}>
      {Math.round(value)}
    </span>
  );
}

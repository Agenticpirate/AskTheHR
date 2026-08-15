import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useReducedMotion } from "motion/react";
import { useRef } from "react";

export function CountUp({
  value,
  className,
  duration = 0.4,
  format,
}: {
  value: number;
  className?: string;
  duration?: number;
  format?: (n: number) => string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const prev = useRef(0);
  const reduce = useReducedMotion();
  const write = (n: number) => (format ? format(n) : String(Math.round(n)));

  useGSAP(() => {
    const el = ref.current;
    if (!el) return;
    if (reduce) {
      el.textContent = write(value);
      prev.current = value;
      return;
    }
    const obj = { n: prev.current };
    gsap.to(obj, {
      n: value,
      duration,
      ease: "power2.out",
      onUpdate: () => {
        el.textContent = write(obj.n);
      },
      onComplete: () => {
        prev.current = value;
      },
    });
  }, [value, reduce, duration]);

  return (
    <span ref={ref} className={className}>
      {write(reduce ? value : prev.current)}
    </span>
  );
}

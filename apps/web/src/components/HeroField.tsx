import { motion, useReducedMotion } from "motion/react";
import type { MouseEvent, ReactNode } from "react";
import { useRef } from "react";

function WordReveal({ text, className }: { text: string; className?: string }) {
  const reduce = useReducedMotion();
  const words = text.split(" ");
  return (
    <h1 className={className}>
      {words.map((word, i) => (
        <motion.span
          key={`${word}-${i}`}
          className="mr-[0.28em] inline-block"
          initial={reduce ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.32, delay: 0.04 * i, ease: [0.22, 1, 0.36, 1] }}
        >
          {word}
        </motion.span>
      ))}
    </h1>
  );
}

export function HeroField({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const onMove = (e: MouseEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--spot-x", `${e.clientX - r.left}px`);
    el.style.setProperty("--spot-y", `${e.clientY - r.top}px`);
  };

  return (
    <div ref={ref} onMouseMove={onMove} className="relative overflow-hidden rounded-lg">
      <div className="hero-field pointer-events-none absolute inset-0" />
      <div className="relative px-2 py-10 md:px-4 md:py-16">{children}</div>
    </div>
  );
}

export function HeroHeadline() {
  const reduce = useReducedMotion();
  return (
    <div className="max-w-3xl">
      <div className="micro text-primary">0pening · AskTheHR</div>
      <WordReveal
        text="Stay in the hunt."
        className="mt-4 text-5xl leading-[0.95] tracking-tight md:text-7xl"
      />
      <motion.p
        className="mt-5 max-w-xl text-lg text-muted-foreground md:text-xl"
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
      >
        Discipline is the product.
      </motion.p>
    </div>
  );
}

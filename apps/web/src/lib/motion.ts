import type { Transition, Variants } from "motion/react";

/** Linear / Vercel: short travel, 150–400ms, no bounce. */
export const easeOut = [0.22, 1, 0.36, 1] as const;

export const fadeRise: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.28, ease: easeOut },
  },
};

export const stagger: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.045, delayChildren: 0.03 },
  },
};

export const staggerFast: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.018, delayChildren: 0.02 },
  },
};

export const staggerHeat: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.012, delayChildren: 0.02 },
  },
};

export const itemRise: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.22, ease: easeOut },
  },
};

/** Opacity only — `transform` on table-row is ignored by browsers. */
export const rowFade: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: 0.2, ease: easeOut },
  },
};

/** Heatmap cells: scale+fade, not a 14px slide on a 16px square. */
export const cellPop: Variants = {
  hidden: { opacity: 0, scale: 0.55 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.18, ease: easeOut },
  },
};

export const hoverLift = {
  y: -1,
  transition: { duration: 0.16, ease: easeOut },
};

export function enterTransition(delay = 0): Transition {
  return { duration: 0.28, delay, ease: easeOut };
}

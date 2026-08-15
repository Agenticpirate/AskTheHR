import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className="mb-10 flex flex-wrap items-end justify-between gap-6"
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="min-w-0 max-w-2xl">
        {eyebrow ? <div className="micro mb-2 text-primary">{eyebrow}</div> : null}
        <h1 className="text-4xl tracking-tight md:text-5xl">{title}</h1>
        {description ? (
          <p className="mt-3 text-base leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </motion.div>
  );
}

import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";
import { HeroField } from "@/components/HeroField";
import { Button } from "@/components/ui/button";

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

export function MarketingHero() {
  const reduce = useReducedMotion();
  return (
    <HeroField>
      <div className="max-w-3xl">
        <div className="micro text-primary">AskTheHR · Cadence</div>
        <WordReveal
          text="The job search fails on discipline, not information."
          className="mt-4 text-5xl leading-[0.95] tracking-tight md:text-7xl"
        />
        <motion.p
          className="mt-5 max-w-xl text-lg text-muted-foreground md:text-xl"
          initial={reduce ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, delay: 0.28, ease: [0.22, 1, 0.36, 1] }}
        >
          Cadence is paid accountability. 0penings is the free employer-direct job
          board inside it. Discipline is the product.
        </motion.p>
        <motion.div
          className="mt-8 flex flex-wrap gap-3"
          initial={reduce ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, delay: 0.36, ease: [0.22, 1, 0.36, 1] }}
        >
          <Button asChild>
            <Link to="/me">Start Cadence</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/jobs">Browse 0penings</Link>
          </Button>
        </motion.div>
      </div>
    </HeroField>
  );
}

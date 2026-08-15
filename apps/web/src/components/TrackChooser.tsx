import { motion, useReducedMotion } from "motion/react";
import { TRACKS, type TrackId } from "@/lib/tracker";
import { itemRise, stagger } from "@/lib/motion";

export function TrackChooser({ onPick }: { onPick: (track: TrackId) => void }) {
  const reduce = useReducedMotion();
  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col justify-center px-6 py-16 md:px-12">
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
        className="mb-12 max-w-2xl"
      >
        <div className="micro text-primary">Choose a track</div>
        <h1 className="mt-3 text-4xl tracking-tight md:text-6xl">Discipline is the product.</h1>
        <p className="mt-4 max-w-lg text-sm leading-relaxed text-muted-foreground">
          Job seekers fail on discipline, not information. Pick once. Daily numbers stay executable.
          You can switch later in Setup.
        </p>
      </motion.div>
      <motion.div
        className="grid gap-4 md:grid-cols-2"
        initial={reduce ? "show" : "hidden"}
        animate="show"
        variants={stagger}
      >
        {(Object.keys(TRACKS) as TrackId[]).map((id) => {
          const t = TRACKS[id];
          return (
            <motion.button
              key={id}
              type="button"
              variants={itemRise}
              whileHover={reduce ? undefined : { y: -1, filter: "brightness(1.06)" }}
              whileTap={reduce ? undefined : { scale: 0.99 }}
              onClick={() => onPick(id)}
              className="rounded-lg bg-card px-6 py-8 text-left ring-1 ring-border"
            >
              <div className="micro text-primary">{t.label}</div>
              <div className="mt-3 font-heading text-3xl tracking-tight">{t.label}</div>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{t.blurb}</p>
              <dl className="mt-6 grid grid-cols-2 gap-3 font-mono text-sm tabular-nums">
                <div>
                  <dt className="micro">Time</dt>
                  <dd className="mt-1">{t.dailyMinutes} min</dd>
                </div>
                <div>
                  <dt className="micro">Apps</dt>
                  <dd className="mt-1">{t.dailyApps} / day</dd>
                </div>
                <div>
                  <dt className="micro">Skills</dt>
                  <dd className="mt-1">{t.dailySkillMinutes} min</dd>
                </div>
                <div>
                  <dt className="micro">Outreach</dt>
                  <dd className="mt-1">{t.dailyOutreach} / day</dd>
                </div>
              </dl>
              <div className="micro mt-6">Weekly target {t.weeklyTarget}</div>
            </motion.button>
          );
        })}
      </motion.div>
    </div>
  );
}

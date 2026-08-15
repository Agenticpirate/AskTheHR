import { Link } from "react-router-dom";
import { CheckInButton } from "@/components/Orb";
import { CountUp } from "@/components/CountUp";
import { Heatmap } from "@/components/Heatmap";
import { PageEnter, Section, Stagger, StaggerItem } from "@/components/PageEnter";
import { ReminderSettings } from "@/components/ReminderSettings";
import { ShareCard } from "@/components/ShareCard";
import { XpBar } from "@/components/XpBar";
import { Button } from "@/components/ui/button";
import { formatShortDate } from "@/lib/dates";
import { BADGE_META, BADGE_ORDER } from "@/lib/tracker";
import { useTracker } from "@/lib/useTracker";

function Kpi({
  label,
  value,
  hint,
}: {
  label: string;
  value: number;
  hint: string;
}) {
  return (
    <div className="rounded-lg bg-card px-4 py-3 ring-1 ring-border">
      <div className="micro">{label}</div>
      <div className="mt-1.5 font-display text-3xl leading-none tracking-tight md:text-4xl">
        <CountUp value={value} />
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

export function Streak() {
  const tracker = useTracker();
  const remaining = Math.max(0, tracker.target - tracker.thisWeek);

  return (
    <PageEnter>
      <Section className="mb-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="micro text-primary">Cadence</div>
            <h1 className="mt-1 text-2xl tracking-tight md:text-3xl">Discipline</h1>
          </div>
          <CheckInButton checkedIn={tracker.today.checkedIn} onCheckIn={() => tracker.checkIn()} />
        </div>
      </Section>

      <Section delay={0.04} className="mb-5">
        <div className="flex items-center justify-between gap-4 rounded-lg bg-foreground px-4 py-3 text-background">
          <div>
            <div className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] opacity-50">
              Today
            </div>
            <div className="mt-1 text-lg tracking-tight">
              {tracker.today.checkedIn ? "Checked in" : "Not checked in"}
            </div>
          </div>
          <p className="max-w-[14rem] text-right text-xs leading-relaxed opacity-60">
            {tracker.today.checkedIn
              ? "On the board. Keep the chain."
              : "One tap starts today."}
          </p>
        </div>
      </Section>

      <Section delay={0.08} className="mb-5">
        <Stagger className="grid grid-cols-2 gap-2 lg:grid-cols-4" fast>
          <StaggerItem>
            <Kpi
              label="Daily streak"
              value={tracker.dailyStreak}
              hint={tracker.dailyStreak === 1 ? "Day of activity" : "Consecutive active days"}
            />
          </StaggerItem>
          <StaggerItem>
            <Kpi
              label="Weekly streak"
              value={tracker.streak}
              hint={`Weeks hitting ${tracker.target} apps`}
            />
          </StaggerItem>
          <StaggerItem>
            <div className="rounded-lg bg-card px-4 py-3 ring-1 ring-border">
              <div className="micro">XP / level</div>
              <div className="mt-1.5 font-display text-3xl leading-none tracking-tight md:text-4xl">
                <CountUp value={tracker.xp} />
              </div>
              <div className="mt-2">
                <XpBar xp={tracker.xp} level={tracker.level} />
              </div>
            </div>
          </StaggerItem>
          <StaggerItem>
            <Kpi
              label="Apps this week"
              value={tracker.thisWeek}
              hint={
                tracker.thisWeek >= tracker.target
                  ? `of ${tracker.target} · target hit`
                  : `of ${tracker.target} · ${remaining} left`
              }
            />
          </StaggerItem>
        </Stagger>
      </Section>

      <Section delay={0.12} className="mb-5">
        <div className="rounded-lg bg-card px-4 py-3 ring-1 ring-border">
          <Heatmap state={tracker.state} />
        </div>
      </Section>

      <Section delay={0.16} className="mb-5">
        <div className="mb-2 flex items-baseline justify-between gap-3">
          <div className="micro">Badges</div>
          <div className="font-mono text-[11px] tabular-nums text-muted-foreground">
            {tracker.badges.length}/{BADGE_ORDER.length}
          </div>
        </div>
        <Stagger className="flex flex-wrap gap-1.5" fast>
          {BADGE_ORDER.map((id) => {
            const unlocked = tracker.badges.includes(id);
            const meta = BADGE_META[id];
            return (
              <StaggerItem key={id}>
                <span
                  title={meta?.hint}
                  className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs ring-1 ${
                    unlocked
                      ? "bg-card text-foreground ring-border"
                      : "bg-muted/40 text-muted-foreground ring-border/70"
                  }`}
                >
                  <span
                    className={`size-1.5 rounded-full ${unlocked ? "bg-primary" : "bg-foreground/20"}`}
                  />
                  {meta?.label ?? id}
                </span>
              </StaggerItem>
            );
          })}
        </Stagger>
      </Section>

      <Section delay={0.2} className="mb-5">
        <div className="micro mb-2">Unlocks</div>
        {tracker.unlocks.length === 0 ? (
          <div className="flex items-center justify-between gap-3 rounded-lg px-4 py-3 text-sm text-muted-foreground ring-1 ring-border">
            <span>Nothing unlocked yet.</span>
            <Button variant="ghost" size="sm" asChild className="h-7 px-2">
              <Link to="/me">Open Me</Link>
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-border rounded-lg ring-1 ring-border">
            {tracker.unlocks.map((row) => (
              <li key={row.id} className="flex items-center justify-between gap-4 px-4 py-2">
                <span className="text-sm tracking-tight">{BADGE_META[row.id]?.label ?? row.id}</span>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {formatShortDate(row.at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section delay={0.24} className="mb-5">
        <ShareCard
          state={tracker.state}
          text={tracker.shareText}
          dailyStreak={tracker.dailyStreak}
          onCopied={tracker.markShared}
        />
      </Section>

      <Section delay={0.28}>
        <ReminderSettings />
      </Section>
    </PageEnter>
  );
}

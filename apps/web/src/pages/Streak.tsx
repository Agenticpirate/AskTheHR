import { Link } from "react-router-dom";
import { CheckInButton } from "@/components/Orb";
import { CountUp } from "@/components/CountUp";
import { Heatmap } from "@/components/Heatmap";
import { PageEnter, Section, Stagger, StaggerItem } from "@/components/PageEnter";
import { ReminderSettings } from "@/components/ReminderSettings";
import { ShareCard } from "@/components/ShareCard";
import { XpBar } from "@/components/XpBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatShortDate } from "@/lib/dates";
import { BADGE_META, BADGE_ORDER } from "@/lib/tracker";
import { useTracker } from "@/lib/useTracker";

export function Streak() {
  const tracker = useTracker();

  return (
    <PageEnter>
      <Section className="mb-12">
        <div className="micro text-primary">Achievements</div>
        <h1 className="mt-3 text-5xl tracking-tight md:text-6xl">Streak.</h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg">
          Daily and weekly discipline, badges, and XP. Browser reminders are free. WhatsApp is
          paid-only.
        </p>
        <div className="mt-6">
          <CheckInButton checkedIn={tracker.today.checkedIn} onCheckIn={() => tracker.checkIn()} />
        </div>
      </Section>

      <Section delay={0.06} className="mb-12">
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="px-2 py-4 md:px-4 md:py-6">
            <CardContent>
              <div className="micro text-primary">Daily streak</div>
              <div className="mt-4 font-display text-6xl leading-none tracking-tight md:text-7xl">
                <CountUp value={tracker.dailyStreak} />
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                {tracker.dailyStreak === 1 ? "Day of activity" : "Consecutive active days"}
              </p>
            </CardContent>
          </Card>
          <Card className="px-2 py-4 md:px-4 md:py-6">
            <CardContent>
              <div className="micro text-primary">Weekly streak</div>
              <div className="mt-4 font-display text-6xl leading-none tracking-tight md:text-7xl">
                <CountUp value={tracker.streak} />
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                Weeks hitting {tracker.target} applications
              </p>
            </CardContent>
          </Card>
        </div>
      </Section>

      <Section delay={0.1} className="mb-12">
        <div className="mb-4">
          <div className="micro">Level</div>
          <h2 className="mt-1 text-3xl tracking-tight">{tracker.level.name}</h2>
        </div>
        <XpBar xp={tracker.xp} level={tracker.level} />
      </Section>

      <Section delay={0.14} className="mb-12">
        <div className="mb-5">
          <div className="micro">Badges</div>
          <h2 className="mt-1 text-3xl tracking-tight">Earned and upcoming.</h2>
        </div>
        <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" fast>
          {BADGE_ORDER.map((id) => {
            const unlocked = tracker.badges.includes(id);
            const meta = BADGE_META[id];
            return (
              <StaggerItem key={id}>
                <div
                  className={`rounded-lg px-5 py-6 ring-1 ring-border ${
                    unlocked ? "bg-card" : "bg-muted/40"
                  }`}
                >
                  <div className="micro text-primary">{unlocked ? "Unlocked" : "Locked"}</div>
                  <div className={`mt-3 text-lg tracking-tight ${unlocked ? "" : "text-muted-foreground"}`}>
                    {meta?.label ?? id}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{meta?.hint}</p>
                </div>
              </StaggerItem>
            );
          })}
        </Stagger>
      </Section>

      <Section delay={0.18} className="mb-12">
        <div className="mb-5">
          <div className="micro">Recent</div>
          <h2 className="mt-1 text-3xl tracking-tight">Unlocks.</h2>
        </div>
        {tracker.unlocks.length === 0 ? (
          <div className="rounded-lg px-6 py-12 text-sm text-muted-foreground ring-1 ring-border">
            Nothing unlocked yet. Log an application or check in on Me.
            <div className="mt-4">
              <Button asChild>
                <Link to="/me">Open Me</Link>
              </Button>
            </div>
          </div>
        ) : (
          <ul className="grid gap-3">
            {tracker.unlocks.map((row) => (
              <li
                key={row.id}
                className="flex items-baseline justify-between gap-4 rounded-lg px-5 py-4 ring-1 ring-border"
              >
                <span className="text-base tracking-tight">
                  {BADGE_META[row.id]?.label ?? row.id}
                </span>
                <span className="font-mono text-xs text-muted-foreground">
                  {formatShortDate(row.at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section delay={0.22} className="mb-12">
        <Heatmap state={tracker.state} />
      </Section>

      <Section delay={0.26} className="mb-12">
        <div className="micro mb-4">Share</div>
        <ShareCard
          state={tracker.state}
          text={tracker.shareText}
          dailyStreak={tracker.dailyStreak}
          onCopied={tracker.markShared}
        />
      </Section>

      <Section delay={0.3}>
        <ReminderSettings />
      </Section>
    </PageEnter>
  );
}

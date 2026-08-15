import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Heatmap } from "@/components/Heatmap";
import { PageEnter, Section } from "@/components/PageEnter";
import { PipelineTable } from "@/components/PipelineTable";
import { ShareCard } from "@/components/ShareCard";
import { TodayRings } from "@/components/TodayRings";
import { TrackChooser } from "@/components/TrackChooser";
import { XpBar } from "@/components/XpBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatMissionDate, formatWeekLabel, weekKey } from "@/lib/dates";
import { publishEntry, unpublishEntry } from "@/lib/leaderboard";
import { BADGE_META, TRACKS, type RingId } from "@/lib/tracker";
import { useTracker } from "@/lib/useTracker";

export function Me() {
  const tracker = useTracker();
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const [skillNote, setSkillNote] = useState(tracker.today.skillNote ?? "");
  const [busy, setBusy] = useState(false);
  const remaining = Math.max(0, tracker.target - tracker.thisWeek);

  if (!tracker.track) {
    return <TrackChooser onPick={tracker.setTrack} />;
  }

  const onManual = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    tracker.log({
      title: title.trim(),
      company: company.trim() || "Unlisted company",
      url: url.trim() || undefined,
    });
    setTitle("");
    setCompany("");
    setUrl("");
  };

  const onAdjust = (id: RingId) => {
    if (id === "minutes") tracker.addMinutes(15);
    if (id === "outreach") tracker.addOutreach(1);
    if (id === "skill") tracker.addSkill(15, skillNote || undefined);
  };

  const togglePublish = async () => {
    if (!tracker.nickname.trim()) return;
    setBusy(true);
    if (tracker.published) {
      await unpublishEntry(tracker.publicId);
      tracker.setPublished(false);
    } else {
      const okTrack = tracker.track;
      if (okTrack !== "fresh" && okTrack !== "experienced") {
        setBusy(false);
        return;
      }
      await publishEntry({
        id: tracker.publicId,
        nickname: tracker.nickname.trim(),
        track: okTrack,
        dailyStreak: tracker.dailyStreak,
        weeklyStreak: tracker.streak,
        xp: tracker.xp,
        level: tracker.level.name,
        publishedAt: new Date().toISOString(),
      });
      tracker.setPublished(true);
    }
    setBusy(false);
  };

  return (
    <PageEnter>
      <Section className="mb-10">
        <div className="micro text-primary">{formatMissionDate()}</div>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-4xl tracking-tight md:text-5xl">
              {tracker.nickname ? tracker.nickname : "Command"}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {TRACKS[tracker.track].label} · daily streak {tracker.dailyStreak} · week {tracker.thisWeek}/
              {tracker.target}
            </p>
          </div>
          <div className="w-full max-w-xs">
            <XpBar xp={tracker.xp} level={tracker.level} />
          </div>
        </div>
      </Section>

      <Section delay={0.06} className="mb-8">
        <TodayRings rings={tracker.rings} onAdjust={onAdjust} />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button
            type="button"
            disabled={tracker.today.checkedIn}
            onClick={() => tracker.checkIn()}
          >
            {tracker.today.checkedIn ? "Checked in" : "I'm here today"}
          </Button>
          <label className="grid min-w-[220px] flex-1 gap-1.5">
            <span className="micro">Skill note</span>
            <Input
              value={skillNote}
              placeholder="What you practiced"
              onChange={(e) => setSkillNote(e.target.value)}
              onBlur={() => tracker.setSkillNote(skillNote)}
            />
          </label>
        </div>
      </Section>

      <Section delay={0.1} className="mb-8">
        <Card>
          <CardHeader>
            <div className="micro text-primary">This week</div>
            <CardTitle className="text-2xl">{formatWeekLabel(weekKey(new Date()))}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full bg-primary"
                style={{
                  width: `${Math.min(100, Math.round((tracker.thisWeek / Math.max(tracker.target, 1)) * 100))}%`,
                }}
              />
            </div>
            <p className="text-sm text-muted-foreground">
              {tracker.thisWeek} of {tracker.target} applications
              {tracker.thisWeek >= tracker.target
                ? " · target hit."
                : ` · ${remaining} remaining.`}
            </p>
          </CardContent>
        </Card>
      </Section>

      <Section delay={0.14} className="mb-8">
        <Heatmap state={tracker.state} />
      </Section>

      <Section delay={0.18} className="mb-8">
        <div className="mb-3 flex items-end justify-between">
          <div>
            <div className="micro">Pipeline</div>
            <h2 className="text-2xl tracking-tight">Applications</h2>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link to="/jobs?work=remote">Find a role</Link>
          </Button>
        </div>
        <PipelineTable
          applications={tracker.state.applications}
          onStatus={tracker.setStatus}
          onRemove={tracker.remove}
        />
        <p className="mt-3 text-xs text-muted-foreground">
          {tracker.state.applications.length} total
        </p>
      </Section>

      <Section delay={0.22} className="mb-8 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Log an application</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onManual} className="grid gap-3">
              <label className="grid gap-1.5">
                <span className="micro">Role</span>
                <Input
                  value={title}
                  required
                  placeholder="Staff product designer"
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label className="grid gap-1.5">
                <span className="micro">Company</span>
                <Input
                  value={company}
                  placeholder="Company"
                  onChange={(e) => setCompany(e.target.value)}
                />
              </label>
              <label className="grid gap-1.5">
                <span className="micro">Apply URL</span>
                <Input
                  value={url}
                  placeholder="https://"
                  onChange={(e) => setUrl(e.target.value)}
                />
              </label>
              <Button type="submit">Add to today</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Setup</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <label className="grid gap-1.5">
              <span className="micro">Nickname</span>
              <Input
                value={tracker.nickname}
                placeholder="Shown on the board"
                onChange={(e) => tracker.setNickname(e.target.value)}
              />
            </label>
            <label className="grid gap-1.5">
              <span className="micro">Track</span>
              <select
                className="h-9 rounded-md border border-border bg-background px-3 text-sm"
                value={tracker.track}
                onChange={(e) => tracker.setTrack(e.target.value as "fresh" | "experienced")}
              >
                <option value="fresh">Fresh</option>
                <option value="experienced">Experienced</option>
              </select>
            </label>
            <label className="grid gap-1.5">
              <span className="micro">Weekly target</span>
              <Input
                type="number"
                min={1}
                max={40}
                value={tracker.target}
                onChange={(e) => tracker.setTarget(Number(e.target.value))}
              />
            </label>
            <Button
              type="button"
              variant={tracker.published ? "outline" : "default"}
              disabled={busy || !tracker.nickname.trim()}
              onClick={() => void togglePublish()}
            >
              {tracker.published ? "Unpublish my streak" : "Publish my streak"}
            </Button>
            <p className="text-xs text-muted-foreground">
              {tracker.nickname.trim()
                ? "Opt-in only. The board never shows your id."
                : "Add a nickname to publish."}{" "}
              <Link to="/board" className="text-primary underline-offset-4 hover:underline">
                View board
              </Link>
            </p>
          </CardContent>
        </Card>
      </Section>

      <Section delay={0.26} className="mb-8">
        <div className="micro mb-3">Share</div>
        <ShareCard
          state={tracker.state}
          text={tracker.shareText}
          dailyStreak={tracker.dailyStreak}
          onCopied={tracker.markShared}
        />
      </Section>

      {tracker.badges.length > 0 ? (
        <Section delay={0.3}>
          <div className="micro mb-3">Badges</div>
          <div className="flex flex-wrap gap-2">
            {tracker.badges.map((id) => (
              <span
                key={id}
                className="rounded-full px-3 py-1 text-xs ring-1 ring-border"
                title={BADGE_META[id]?.hint}
              >
                {BADGE_META[id]?.label ?? id}
              </span>
            ))}
          </div>
        </Section>
      ) : null}
    </PageEnter>
  );
}

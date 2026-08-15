import { Link } from "react-router-dom";
import { HeroField, HeroHeadline } from "@/components/HeroField";
import { JobTable } from "@/components/JobTable";
import { BoardLoading } from "@/components/Orb";
import { KpiCard } from "@/components/KpiCard";
import { PageEnter, Section, Stagger, StaggerItem } from "@/components/PageEnter";
import { TodayRings } from "@/components/TodayRings";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { COUNTRIES, COUNTRY_META } from "@/data/countries";
import { formatCompact, formatCount, formatPercent } from "@/lib/format";
import { featuredRemote } from "@/lib/jobs";
import { useJobs } from "@/lib/useJobs";
import { useTracker } from "@/lib/useTracker";

export function Home() {
  const { data, error, loading } = useJobs(false);
  const tracker = useTracker();
  const jobs = data?.jobs ?? [];
  const featured = featuredRemote(jobs, 8);
  const counts = data?.by_country ?? {};
  const total = data?.total ?? 0;
  const remote = data?.by_remote?.remote ?? 0;
  const onsite = data?.by_remote?.onsite ?? 0;
  const classified = remote + onsite;
  const remoteShare = classified > 0 ? remote / classified : 0;

  return (
    <PageEnter>
      <HeroField>
        <HeroHeadline />
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild>
            <Link to="/jobs?work=remote">Remote board</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/me">{tracker.track ? "Open Me" : "Pick a track"}</Link>
          </Button>
          <Button variant="ghost" asChild>
            <Link to="/streak">Streak</Link>
          </Button>
        </div>
      </HeroField>

      <Section delay={0.12} className="mt-10">
        {tracker.track ? (
          <TodayRings rings={tracker.rings} compact />
        ) : (
          <div className="rounded-lg px-6 py-10 ring-1 ring-border">
            <div className="micro text-primary">Accountability</div>
            <h2 className="mt-2 text-2xl tracking-tight">Choose Fresh or Experienced.</h2>
            <p className="mt-2 max-w-lg text-sm text-muted-foreground">
              Daily minutes, tailored apps, skills, and outreach. Vague weekly targets fail.
            </p>
            <Button asChild className="mt-5">
              <Link to="/me">Start the loop</Link>
            </Button>
          </div>
        )}
      </Section>

      <Section delay={0.18} className="mt-10">
        <Stagger className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StaggerItem>
            <KpiCard
              label="Openings"
              value={loading ? "—" : formatCompact(total)}
              hint={total ? `${formatCount(total)} collected` : "From jobs.json"}
            />
          </StaggerItem>
          <StaggerItem>
            <KpiCard
              label="Remote share"
              value={loading ? "—" : formatPercent(remoteShare)}
              hint={remote ? `${formatCount(remote)} remote listings` : "Of classified roles"}
            />
          </StaggerItem>
          <StaggerItem>
            <KpiCard
              label="This week"
              value={`${tracker.thisWeek}`}
              hint={`${tracker.thisWeek} of ${tracker.target} applications`}
            />
          </StaggerItem>
          <StaggerItem>
            <KpiCard
              label="Streak"
              value={`${tracker.dailyStreak}`}
              hint={tracker.dailyStreak === 1 ? "Day checked in" : "Days of activity"}
            />
          </StaggerItem>
        </Stagger>
      </Section>

      <Section delay={0.22} className="mt-10">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <div className="micro">Markets</div>
            <h2 className="text-2xl tracking-tight">Ten countries</h2>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/countries">All markets</Link>
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {COUNTRIES.map((c) => (
            <Link key={c} to={`/countries/${COUNTRY_META[c].slug}`}>
              <Badge variant="outline" className="h-7 gap-1.5 px-2.5 text-xs font-normal">
                <span>{COUNTRY_META[c].flag}</span>
                {c}
                <span className="text-muted-foreground">{formatCompact(counts[c] ?? 0)}</span>
              </Badge>
            </Link>
          ))}
        </div>
      </Section>

      <Section delay={0.26} className="mt-10">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <div className="micro">Featured</div>
            <h2 className="text-2xl tracking-tight">Remote roles</h2>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/jobs?work=remote">See all remote</Link>
          </Button>
        </div>
        {loading ? (
          <BoardLoading label="Loading the board…" />
        ) : (
          <JobTable
            jobs={featured}
            empty={error ? "Job feed unavailable." : "No remote roles in this slice yet."}
          />
        )}
      </Section>
    </PageEnter>
  );
}

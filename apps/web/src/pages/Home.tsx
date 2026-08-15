import { Link } from "react-router-dom";
import { JobTable } from "@/components/JobTable";
import { KpiCard } from "@/components/KpiCard";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { COUNTRIES, COUNTRY_META } from "@/data/countries";
import { formatCompact, formatCount, formatPercent } from "@/lib/format";
import { featuredRemote } from "@/lib/jobs";
import { useJobs } from "@/lib/useJobs";
import { useTracker } from "@/lib/useTracker";

export function Home() {
  const { data, error, loading } = useJobs(false);
  const { thisWeek, target, streak } = useTracker();
  const jobs = data?.jobs ?? [];
  const featured = featuredRemote(jobs, 8);
  const counts = data?.by_country ?? {};
  const total = data?.total ?? 0;
  const remote = data?.by_remote?.remote ?? 0;
  const onsite = data?.by_remote?.onsite ?? 0;
  const classified = remote + onsite;
  const remoteShare = classified > 0 ? remote / classified : 0;

  return (
    <>
      <PageHeader
        eyebrow="August 2026"
        title="Dashboard"
        description={
          loading
            ? "Loading the August board…"
            : error
              ? "Job feed unavailable right now."
              : `${formatCount(total)} openings collected. ${formatCount(data?.shown ?? jobs.length)} on this board.`
        }
        actions={
          <>
            <Button asChild>
              <Link to="/jobs?work=remote">Remote board</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/me">My week</Link>
            </Button>
          </>
        }
      />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Openings"
          value={loading ? "—" : formatCompact(total)}
          hint={total ? `${formatCount(total)} collected` : "From jobs.json"}
        />
        <KpiCard
          label="Remote share"
          value={loading ? "—" : formatPercent(remoteShare)}
          hint={remote ? `${formatCount(remote)} remote listings` : "Of classified roles"}
        />
        <KpiCard
          label="This week"
          value={`${thisWeek}`}
          hint={`${thisWeek} of ${target} applications`}
        />
        <KpiCard
          label="Streak"
          value={`${streak}`}
          hint={streak === 1 ? "Week at target" : "Weeks at target"}
        />
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Markets
            </div>
            <h2 className="font-heading text-2xl tracking-tight">Ten countries</h2>
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
                <span className="text-muted-foreground">
                  {formatCompact(counts[c] ?? 0)}
                </span>
              </Badge>
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Featured
            </div>
            <h2 className="font-heading text-2xl tracking-tight">Remote roles</h2>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/jobs?work=remote">See all remote</Link>
          </Button>
        </div>
        <JobTable
          jobs={featured}
          empty={loading ? "Loading featured roles…" : "No remote roles in this slice yet."}
        />
      </section>
    </>
  );
}

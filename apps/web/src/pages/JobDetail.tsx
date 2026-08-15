import { Link, useParams } from "react-router-dom";
import { JobTable } from "@/components/JobTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPosted } from "@/lib/dates";
import { findJob, locationLabel, similarJobs } from "@/lib/jobs";
import { useJobs } from "@/lib/useJobs";
import { useTracker } from "@/lib/useTracker";

export function JobDetail() {
  const { id = "" } = useParams();
  const decoded = decodeURIComponent(id);
  const { data, loading, loadingMore } = useJobs(true);
  const jobs = data?.jobs ?? [];
  const job = findJob(jobs, decoded);
  const tracker = useTracker();

  if (!job && (loading || loadingMore)) {
    return <p className="text-sm text-muted-foreground">Looking up this role…</p>;
  }
  if (!job) {
    return (
      <div className="rounded-xl px-4 py-16 text-center ring-1 ring-foreground/10">
        <h1 className="font-heading text-3xl tracking-tight">Role not in this build</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          It may have been dropped in the cap, or the link is stale.
        </p>
        <Button asChild className="mt-4">
          <Link to="/jobs">Back to the board</Link>
        </Button>
      </div>
    );
  }

  const applied = tracker.applied(job.id);
  const similar = similarJobs(jobs, job, 4);

  return (
    <>
      <p className="mb-4 text-xs text-muted-foreground">
        <Link to="/jobs" className="hover:text-foreground">
          Jobs
        </Link>
        {job.country ? (
          <>
            {" / "}
            <Link
              to={`/jobs?country=${encodeURIComponent(job.country)}`}
              className="hover:text-foreground"
            >
              {job.country}
            </Link>
          </>
        ) : null}
      </p>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <article>
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-primary">
            {job.company}
          </div>
          <h1 className="font-heading mt-1 text-3xl tracking-tight md:text-4xl">{job.title}</h1>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge variant={job.remote ? "secondary" : "outline"}>
              {job.remote ? "Remote" : "On-site"}
            </Badge>
            <Badge variant="outline">{locationLabel(job)}</Badge>
            <Badge variant="outline">{formatPosted(job.posted_at)}</Badge>
            <Badge variant="outline">{job.source}</Badge>
          </div>
          <div className="prose mt-6 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {job.description ? (
              job.description.split(/\n{2,}/).map((para, i) => (
                <p key={i} className="mb-3 last:mb-0">
                  {para}
                </p>
              ))
            ) : (
              <p>No description was provided by the source. Use the apply link for the full posting.</p>
            )}
          </div>
        </article>

        <aside className="lg:sticky lg:top-16 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle>Apply</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <Button asChild>
                <a href={job.url} target="_blank" rel="noreferrer">
                  Apply on {job.source}
                </a>
              </Button>
              <Button
                type="button"
                variant={applied ? "secondary" : "outline"}
                disabled={applied}
                onClick={() =>
                  tracker.log({
                    jobId: job.id,
                    title: job.title,
                    company: job.company,
                    url: job.url,
                    country: job.country,
                  })
                }
              >
                {applied ? "Logged — you applied" : "I applied"}
              </Button>
              <Button variant="ghost" asChild>
                <Link to="/me">See my week</Link>
              </Button>
            </CardContent>
          </Card>
        </aside>
      </div>

      {similar.length > 0 ? (
        <section className="mt-10">
          <h2 className="font-heading mb-3 text-2xl tracking-tight">Nearby roles</h2>
          <JobTable jobs={similar} />
        </section>
      ) : null}
    </>
  );
}

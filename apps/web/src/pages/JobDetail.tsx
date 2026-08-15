import { Link, useParams } from "react-router-dom";
import { JobCard } from "../components/JobCard";
import { formatPosted } from "../lib/dates";
import { findJob, jobPath, locationLabel, similarJobs } from "../lib/jobs";
import { useJobs } from "../lib/useJobs";
import { useTracker } from "../lib/useTracker";

export function JobDetail() {
  const { id = "" } = useParams();
  const decoded = decodeURIComponent(id);
  const { data, loading, loadingMore } = useJobs(true);
  const jobs = data?.jobs ?? [];
  const job = findJob(jobs, decoded);
  const tracker = useTracker();

  if (!job && (loading || loadingMore)) {
    return <p className="notice">Looking up this role…</p>;
  }
  if (!job) {
    return (
      <div className="empty">
        <h1>Role not in this build</h1>
        <p>It may have been dropped in the cap, or the link is stale.</p>
        <Link className="btn btn-primary" to="/jobs">
          Back to the board
        </Link>
      </div>
    );
  }

  const applied = tracker.applied(job.id);
  const similar = similarJobs(jobs, job, 4);

  return (
    <>
      <p className="notice">
        <Link to="/jobs">Jobs</Link>
        {job.country ? (
          <>
            {" / "}
            <Link to={`/jobs?country=${encodeURIComponent(job.country)}`}>{job.country}</Link>
          </>
        ) : null}
      </p>
      <article className="detail-hero">
        <div className="eyebrow">{job.company}</div>
        <h1>{job.title}</h1>
        <div className="meta">
          <span className={`pill ${job.remote ? "remote" : "onsite"}`}>
            {job.remote ? "Remote" : "On-site"}
          </span>
          <span className="pill">{locationLabel(job)}</span>
          <span className="pill">{formatPosted(job.posted_at)}</span>
          <span className="pill">{job.source}</span>
        </div>
      </article>

      <div className="detail-actions">
        <a className="btn btn-primary" href={job.url} target="_blank" rel="noreferrer">
          Apply on {job.source}
        </a>
        <button
          type="button"
          className={applied ? "btn btn-good" : "btn btn-ghost"}
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
        </button>
        <Link className="btn btn-ghost" to="/me">
          See my week
        </Link>
      </div>

      <div className="prose">
        {job.description ? (
          job.description.split(/\n{2,}/).map((para, i) => <p key={i}>{para}</p>)
        ) : (
          <p>No description was provided by the source. Use the apply link for the full posting.</p>
        )}
      </div>

      {similar.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Nearby roles</h2>
          </div>
          <div className="grid-jobs">
            {similar.map((j) => (
              <JobCard key={j.id} job={j} />
            ))}
          </div>
        </section>
      )}
      <p className="notice" style={{ marginTop: 24 }}>
        Permalink: <Link to={jobPath(job)}>{job.id}</Link>
      </p>
    </>
  );
}

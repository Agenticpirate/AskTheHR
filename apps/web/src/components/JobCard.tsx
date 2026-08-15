import { Link } from "react-router-dom";
import { formatPosted } from "../lib/dates";
import { jobPath, locationLabel, type Job } from "../lib/jobs";

function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  const a = parts[0]?.[0] || "?";
  const b = parts.length > 1 ? parts[parts.length - 1][0] : parts[0]?.[1] || "";
  return (a + b).toUpperCase();
}

export function JobCard({ job }: { job: Job }) {
  return (
    <Link className="job-card" to={jobPath(job)}>
      <div className="job-top">
        <div className="avatar" aria-hidden>
          {initials(job.company)}
        </div>
        <div>
          <h3>{job.title}</h3>
          <div className="co">{job.company}</div>
        </div>
      </div>
      <div className="meta">
        <span className={`pill ${job.remote ? "remote" : "onsite"}`}>
          {job.remote ? "Remote" : "On-site"}
        </span>
        <span className="pill">{locationLabel(job)}</span>
      </div>
      <div className="job-foot">
        <span>{formatPosted(job.posted_at)}</span>
        <span>{job.source}</span>
      </div>
    </Link>
  );
}

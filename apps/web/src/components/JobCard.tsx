import { Link } from "react-router-dom";
import { CompanyLogo } from "@/components/CompanyLogo";
import { Badge } from "@/components/ui/badge";
import { formatPosted } from "@/lib/dates";
import { jobPath, locationLabel, type Job } from "@/lib/jobs";

export function JobCard({ job }: { job: Job }) {
  return (
    <Link
      to={jobPath(job)}
      className="block rounded-xl bg-card p-4 ring-1 ring-foreground/10 transition-colors hover:bg-muted/40"
    >
      <div className="flex items-start gap-3">
        <CompanyLogo url={job.url} company={job.company} size={28} />
        <div className="min-w-0 flex-1">
          <div className="truncate font-medium leading-snug">{job.title}</div>
          <div className="truncate text-sm text-muted-foreground">{job.company}</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <Badge variant={job.remote ? "secondary" : "outline"}>
          {job.remote ? "Remote" : "On-site"}
        </Badge>
        <Badge variant="outline">{locationLabel(job)}</Badge>
      </div>
      <div className="mt-3 text-[11px] text-muted-foreground">
        {formatPosted(job.posted_at)}
      </div>
    </Link>
  );
}

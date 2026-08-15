import { useReducedMotion } from "motion/react";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Table, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CompanyLogo } from "@/components/CompanyLogo";
import { JobCard } from "@/components/JobCard";
import { Stagger } from "@/components/PageEnter";
import { formatPosted } from "@/lib/dates";
import { jobPath, locationLabel, type Job } from "@/lib/jobs";
import { useTableEnter } from "@/lib/useTableEnter";

export function JobTable({
  jobs,
  empty = "No roles match.",
}: {
  jobs: Job[];
  empty?: string;
}) {
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const listKey = jobs.map((j) => j.id).join("|");
  const bodyRef = useTableEnter(listKey, reduce);

  if (jobs.length === 0) {
    return (
      <div className="rounded-lg px-4 py-16 text-center text-sm text-muted-foreground ring-1 ring-border">
        {empty}
      </div>
    );
  }

  return (
    <>
      <div className="hidden overflow-hidden rounded-lg ring-1 ring-border md:block">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Role</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Posted</TableHead>
            </TableRow>
          </TableHeader>
          <tbody ref={bodyRef}>
            {jobs.map((job) => (
              <tr
                key={job.id}
                className="row-lift cursor-pointer border-b hover:bg-muted/50"
                onClick={() => navigate(jobPath(job))}
              >
                <TableCell className="max-w-[280px] whitespace-normal">
                  <div className="row-lift-inner font-medium leading-snug">{job.title}</div>
                </TableCell>
                <TableCell className="max-w-[200px]">
                  <div className="row-lift-inner flex items-center gap-2">
                    <CompanyLogo url={job.url} company={job.company} size={20} />
                    <span className="truncate">{job.company}</span>
                  </div>
                </TableCell>
                <TableCell className="max-w-[200px] truncate text-muted-foreground">
                  <div className="row-lift-inner truncate">{locationLabel(job)}</div>
                </TableCell>
                <TableCell>
                  <div className="row-lift-inner">
                    <Badge variant={job.remote ? "secondary" : "outline"}>
                      {job.remote ? "Remote" : "On-site"}
                    </Badge>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  <div className="row-lift-inner">{formatPosted(job.posted_at)}</div>
                </TableCell>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
      <Stagger className="grid gap-2 md:hidden" fast>
        {jobs.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </Stagger>
    </>
  );
}

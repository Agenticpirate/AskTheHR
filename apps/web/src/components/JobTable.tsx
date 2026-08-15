import { motion, useReducedMotion } from "motion/react";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CompanyLogo } from "@/components/CompanyLogo";
import { formatPosted } from "@/lib/dates";
import { jobPath, locationLabel, type Job } from "@/lib/jobs";
import { itemRise, staggerFast } from "@/lib/motion";

export function JobTable({
  jobs,
  empty = "No roles match.",
}: {
  jobs: Job[];
  empty?: string;
}) {
  const navigate = useNavigate();
  const reduce = useReducedMotion();

  if (jobs.length === 0) {
    return (
      <div className="rounded-lg px-4 py-16 text-center text-sm text-muted-foreground ring-1 ring-border">
        {empty}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg ring-1 ring-border">
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
        <motion.tbody initial={reduce ? "show" : "hidden"} animate="show" variants={staggerFast}>
          {jobs.map((job) => (
            <motion.tr
              key={job.id}
              variants={itemRise}
              className="cursor-pointer border-b hover:bg-muted/50"
              onClick={() => navigate(jobPath(job))}
            >
              <TableCell className="max-w-[280px] whitespace-normal">
                <div className="font-medium leading-snug">{job.title}</div>
                <div className="text-[11px] text-muted-foreground">{job.source}</div>
              </TableCell>
              <TableCell className="max-w-[200px]">
                <div className="flex items-center gap-2">
                  <CompanyLogo url={job.url} company={job.company} size={20} />
                  <span className="truncate">{job.company}</span>
                </div>
              </TableCell>
              <TableCell className="max-w-[200px] truncate text-muted-foreground">
                {locationLabel(job)}
              </TableCell>
              <TableCell>
                <Badge variant={job.remote ? "secondary" : "outline"}>
                  {job.remote ? "Remote" : "On-site"}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatPosted(job.posted_at)}
              </TableCell>
            </motion.tr>
          ))}
        </motion.tbody>
      </Table>
    </div>
  );
}

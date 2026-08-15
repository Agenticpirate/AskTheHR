import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPosted } from "@/lib/dates";
import { jobPath, locationLabel, type Job } from "@/lib/jobs";

export function JobTable({
  jobs,
  empty = "No roles match.",
}: {
  jobs: Job[];
  empty?: string;
}) {
  const navigate = useNavigate();

  if (jobs.length === 0) {
    return (
      <div className="rounded-xl px-4 py-16 text-center text-sm text-muted-foreground ring-1 ring-foreground/10">
        {empty}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">Role</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="pr-4">Posted</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow
              key={job.id}
              className="cursor-pointer"
              onClick={() => navigate(jobPath(job))}
            >
              <TableCell className="max-w-[280px] pl-4 whitespace-normal">
                <div className="font-medium leading-snug">{job.title}</div>
                <div className="text-[11px] text-muted-foreground">{job.source}</div>
              </TableCell>
              <TableCell className="max-w-[180px] truncate">{job.company}</TableCell>
              <TableCell className="max-w-[200px] truncate text-muted-foreground">
                {locationLabel(job)}
              </TableCell>
              <TableCell>
                <Badge variant={job.remote ? "secondary" : "outline"}>
                  {job.remote ? "Remote" : "On-site"}
                </Badge>
              </TableCell>
              <TableCell className="pr-4 text-muted-foreground">
                {formatPosted(job.posted_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

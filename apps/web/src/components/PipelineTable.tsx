import { motion, useReducedMotion } from "motion/react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatShortDate } from "@/lib/dates";
import { itemRise, staggerFast } from "@/lib/motion";
import { APP_STATUSES, STATUS_LABEL, type Application, type AppStatus } from "@/lib/tracker";

export function PipelineTable({
  applications,
  onStatus,
  onRemove,
}: {
  applications: Application[];
  onStatus: (id: string, status: AppStatus) => void;
  onRemove: (id: string) => void;
}) {
  const reduce = useReducedMotion();
  if (applications.length === 0) {
    return (
      <div className="rounded-lg px-4 py-16 text-center text-sm text-muted-foreground ring-1 ring-border">
        Nothing in the pipeline yet. Log a role from the board or add one by hand.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg ring-1 ring-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">Role</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="pr-4 text-right"> </TableHead>
          </TableRow>
        </TableHeader>
        <motion.tbody
          initial={reduce ? "show" : "hidden"}
          animate="show"
          variants={staggerFast}
        >
          {applications.map((a) => (
            <motion.tr
              key={a.id}
              variants={itemRise}
              className="border-b hover:bg-white/[0.03]"
            >
              <TableCell className="max-w-[240px] pl-4 whitespace-normal font-medium">
                {a.title}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {a.company}
                {a.country ? ` · ${a.country}` : ""}
              </TableCell>
              <TableCell className="text-muted-foreground">{formatShortDate(a.appliedAt)}</TableCell>
              <TableCell>
                <select
                  className="h-8 rounded-md border border-border bg-background px-2 text-xs"
                  value={a.status ?? "applied"}
                  onChange={(e) => onStatus(a.id, e.target.value as AppStatus)}
                  aria-label={`Status for ${a.title}`}
                >
                  {APP_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {STATUS_LABEL[s]}
                    </option>
                  ))}
                </select>
              </TableCell>
              <TableCell className="pr-4 text-right">
                <Button type="button" variant="ghost" size="xs" onClick={() => onRemove(a.id)}>
                  Remove
                </Button>
              </TableCell>
            </motion.tr>
          ))}
        </motion.tbody>
      </Table>
    </div>
  );
}

import { useReducedMotion } from "motion/react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatShortDate } from "@/lib/dates";
import { APP_STATUSES, STATUS_LABEL, type Application, type AppStatus } from "@/lib/tracker";
import { useTableEnter } from "@/lib/useTableEnter";

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
  const listKey = applications.map((a) => a.id).join("|");
  const bodyRef = useTableEnter(listKey, reduce);

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
            <TableHead>Role</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right"> </TableHead>
          </TableRow>
        </TableHeader>
        <tbody ref={bodyRef}>
          {applications.map((a) => (
            <tr key={a.id} className="row-lift border-b hover:bg-muted/50">
              <TableCell className="max-w-[240px] whitespace-normal font-medium">
                <div className="row-lift-inner">{a.title}</div>
              </TableCell>
              <TableCell className="text-muted-foreground">
                <div className="row-lift-inner">
                  {a.company}
                  {a.country ? ` · ${a.country}` : ""}
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">
                <div className="row-lift-inner">{formatShortDate(a.appliedAt)}</div>
              </TableCell>
              <TableCell>
                <div className="row-lift-inner">
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
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div className="row-lift-inner">
                  <Button type="button" variant="ghost" size="xs" onClick={() => onRemove(a.id)}>
                    Remove
                  </Button>
                </div>
              </TableCell>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

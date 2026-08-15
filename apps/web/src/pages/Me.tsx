import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatShortDate, formatWeekLabel, weekKey } from "@/lib/dates";
import { useTracker } from "@/lib/useTracker";

export function Me() {
  const tracker = useTracker();
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");
  const pct = Math.min(100, Math.round((tracker.thisWeek / Math.max(tracker.target, 1)) * 100));
  const remaining = Math.max(0, tracker.target - tracker.thisWeek);

  const onManual = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    tracker.log({
      title: title.trim(),
      company: company.trim() || "Unlisted company",
      url: url.trim() || undefined,
    });
    setTitle("");
    setCompany("");
    setUrl("");
  };

  return (
    <>
      <PageHeader
        eyebrow="Accountability"
        title="My week"
        description="Set a weekly target. Log roles from the board or add one by hand. The log stays on this device until auth ships."
      />

      <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <div className="grid gap-4 self-start">
          <Card>
            <CardHeader>
              <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-primary">
                This week
              </div>
              <CardTitle className="font-heading text-2xl">
                {formatWeekLabel(weekKey(new Date()))}
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <Progress value={pct} className="h-1.5" />
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <div className="font-heading text-2xl leading-none">
                    {tracker.thisWeek}/{tracker.target}
                  </div>
                  <div className="mt-1 text-[11px] text-muted-foreground">Applications</div>
                </div>
                <div>
                  <div className="font-heading text-2xl leading-none">{tracker.streak}</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">Streak</div>
                </div>
                <div>
                  <div className="font-heading text-2xl leading-none">{pct}%</div>
                  <div className="mt-1 text-[11px] text-muted-foreground">Of target</div>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {tracker.nickname ? `${tracker.nickname} · ` : ""}
                {tracker.thisWeek >= tracker.target
                  ? "Target hit. Keep going if you want."
                  : `${remaining} more ${remaining === 1 ? "application" : "applications"} to hit the target.`}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Setup</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <label className="grid gap-1.5">
                <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                  Nickname
                </span>
                <Input
                  value={tracker.nickname}
                  placeholder="Optional"
                  onChange={(e) => tracker.setNickname(e.target.value)}
                />
              </label>
              <label className="grid gap-1.5">
                <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                  Weekly target
                </span>
                <Input
                  type="number"
                  min={1}
                  max={40}
                  value={tracker.target}
                  onChange={(e) => tracker.setTarget(Number(e.target.value))}
                />
              </label>
              <p className="text-xs text-muted-foreground">
                A week runs Monday–Sunday. Hit the number and the streak holds.
              </p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="log">
          <TabsList>
            <TabsTrigger value="log">Application log</TabsTrigger>
            <TabsTrigger value="add">Add by hand</TabsTrigger>
          </TabsList>
          <TabsContent value="log" className="mt-3">
            {tracker.state.applications.length === 0 ? (
              <div className="rounded-xl px-4 py-16 text-center text-sm text-muted-foreground ring-1 ring-foreground/10">
                Nothing logged yet.{" "}
                <Link to="/jobs?work=remote" className="text-foreground underline-offset-4 hover:underline">
                  Pick a remote role
                </Link>{" "}
                and press “I applied”.
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl ring-1 ring-foreground/10">
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="pl-4">Role</TableHead>
                      <TableHead>Company</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead className="pr-4 text-right"> </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tracker.state.applications.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell className="max-w-[240px] pl-4 whitespace-normal font-medium">
                          {a.title}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {a.company}
                          {a.country ? ` · ${a.country}` : ""}
                          {a.url ? (
                            <>
                              {" · "}
                              <a
                                href={a.url}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:text-foreground"
                              >
                                listing
                              </a>
                            </>
                          ) : null}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatShortDate(a.appliedAt)}
                        </TableCell>
                        <TableCell className="pr-4 text-right">
                          <Button
                            type="button"
                            variant="ghost"
                            size="xs"
                            onClick={() => tracker.remove(a.id)}
                          >
                            Remove
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              {tracker.state.applications.length} total
            </p>
          </TabsContent>
          <TabsContent value="add" className="mt-3">
            <Card>
              <CardHeader>
                <CardTitle>Log an application</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={onManual} className="grid gap-3">
                  <label className="grid gap-1.5">
                    <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                      Role
                    </span>
                    <Input
                      value={title}
                      required
                      placeholder="Staff product designer"
                      onChange={(e) => setTitle(e.target.value)}
                    />
                  </label>
                  <label className="grid gap-1.5">
                    <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                      Company
                    </span>
                    <Input
                      value={company}
                      placeholder="Company"
                      onChange={(e) => setCompany(e.target.value)}
                    />
                  </label>
                  <label className="grid gap-1.5">
                    <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                      Apply URL
                    </span>
                    <Input
                      value={url}
                      placeholder="https://"
                      onChange={(e) => setUrl(e.target.value)}
                    />
                  </label>
                  <Button type="submit">Add to this week</Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}

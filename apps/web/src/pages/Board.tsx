import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";
import { CountUp } from "@/components/CountUp";
import { PageEnter, Section } from "@/components/PageEnter";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchBoard, type BoardEntry, type BoardResult } from "@/lib/leaderboard";
import { itemRise, stagger } from "@/lib/motion";
import { TRACKS } from "@/lib/tracker";
import { useTracker } from "@/lib/useTracker";

export function Board() {
  const tracker = useTracker();
  const reduce = useReducedMotion();
  const [result, setResult] = useState<BoardResult | null>(null);

  useEffect(() => {
    let live = true;
    void fetchBoard().then((next) => {
      if (live) setResult(next);
    });
    return () => {
      live = false;
    };
  }, [tracker.published, tracker.xp, tracker.dailyStreak]);

  const entries = result?.entries ?? [];

  return (
    <PageEnter>
      <Section>
        <div className="micro text-primary">Public</div>
        <h1 className="mt-3 text-5xl tracking-tight md:text-6xl">Board.</h1>
        <p className="mt-3 max-w-xl text-sm text-muted-foreground">
          Ranked by daily streak, then weekly streak, then XP. Opt-in from Me. No accounts.
        </p>
      </Section>

      {result?.message ? (
        <Section delay={0.08} className="mt-6">
          <p className="text-sm text-muted-foreground">{result.message}</p>
        </Section>
      ) : null}

      <Section delay={0.12} className="mt-8">
        {entries.length === 0 ? (
          <div className="rounded-lg px-6 py-16 text-center ring-1 ring-border">
            <h2 className="text-2xl tracking-tight">Be the first streak.</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Publish from Me with a nickname. We never invent names.
            </p>
            <Button asChild className="mt-5">
              <Link to="/me">Go to Me</Link>
            </Button>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg ring-1 ring-border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Rank</TableHead>
                  <TableHead>Seeker</TableHead>
                  <TableHead>Track</TableHead>
                  <TableHead>Daily</TableHead>
                  <TableHead>Weekly</TableHead>
                  <TableHead>Level</TableHead>
                  <TableHead>XP</TableHead>
                </TableRow>
              </TableHeader>
              <motion.tbody
                initial={reduce ? "show" : "hidden"}
                animate="show"
                variants={stagger}
              >
                {entries.map((row, i) => (
                  <BoardRow
                    key={row.id}
                    row={row}
                    rank={i + 1}
                    mine={row.id === tracker.publicId}
                  />
                ))}
              </motion.tbody>
            </Table>
          </div>
        )}
      </Section>
    </PageEnter>
  );
}

function BoardRow({
  row,
  rank,
  mine,
}: {
  row: BoardEntry;
  rank: number;
  mine: boolean;
}) {
  return (
    <motion.tr
      variants={itemRise}
      className={`border-b ${mine ? "bg-primary/10" : "hover:bg-muted/50"}`}
    >
      <TableCell className="font-mono tabular-nums">
        <CountUp value={rank} duration={0.5} />
      </TableCell>
      <TableCell className="font-medium">
        {row.nickname}
        {mine ? <span className="ml-2 text-xs text-primary">You</span> : null}
      </TableCell>
      <TableCell className="text-muted-foreground">{TRACKS[row.track].label}</TableCell>
      <TableCell className="font-mono tabular-nums">{row.dailyStreak}</TableCell>
      <TableCell className="font-mono tabular-nums">{row.weeklyStreak}</TableCell>
      <TableCell>{row.level}</TableCell>
      <TableCell className="font-mono tabular-nums">{row.xp}</TableCell>
    </motion.tr>
  );
}

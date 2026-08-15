import { Link } from "react-router-dom";
import { Section } from "@/components/PageEnter";
import { Button } from "@/components/ui/button";

export function JobBoardExplain() {
  return (
    <Section id="board-explain" delay={0.14} className="marketing-defer scroll-mt-20">
      <div className="micro text-primary">Is it a job board?</div>
      <h2 className="mt-2 max-w-2xl text-3xl tracking-tight md:text-5xl">
        A board, not a marketplace.
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground md:text-base">
        0penings is a free employer-direct discovery slice inside Cadence. Cadence is
        not a job board. AskTheHR does not take applications, run an ATS, or sit
        between you and the company.
      </p>
      <div className="mt-10 grid gap-3 md:grid-cols-2">
        <article className="flex flex-col gap-3 rounded-lg bg-card px-5 py-6 ring-1 ring-border">
          <div className="micro text-primary">Cadence</div>
          <h3 className="text-xl tracking-tight">Paid accountability</h3>
          <ul className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
            <li>Daily rings and a weekly number.</li>
            <li>Streak resets if you miss the week.</li>
            <li>Reminders on the device. WhatsApp on a paid plan.</li>
            <li>No feed. No account required to start.</li>
          </ul>
        </article>
        <article className="flex flex-col gap-3 rounded-lg bg-card px-5 py-6 ring-1 ring-border">
          <div className="micro text-primary">0penings</div>
          <h3 className="text-xl tracking-tight">Free employer-direct board</h3>
          <ul className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
            <li>Ten countries. Remote first. On-site still filterable.</li>
            <li>Apply opens the employer career site or ATS.</li>
            <li>Log the application so the week stays honest.</li>
            <li>Not an aggregator form in the middle.</li>
          </ul>
        </article>
      </div>
      <div className="mt-6">
        <Button variant="outline" asChild>
          <Link to="/jobs">Browse 0penings</Link>
        </Button>
      </div>
    </Section>
  );
}

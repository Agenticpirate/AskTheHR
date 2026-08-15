import { Section } from "@/components/PageEnter";

export function AeoAnswer() {
  return (
    <Section delay={0.08} className="mt-4">
      <article
        id="answer"
        className="rounded-lg px-6 py-8 ring-1 ring-border md:px-8"
        aria-labelledby="aeo-question"
      >
        <div className="micro text-primary">Answer</div>
        <h2 id="aeo-question" className="mt-2 text-2xl tracking-tight md:text-3xl">
          What is AskTheHR?
        </h2>
        <p className="mt-4 max-w-3xl text-base leading-relaxed text-muted-foreground">
          AskTheHR is the company. <strong className="font-medium text-foreground">Cadence</strong>{" "}
          is paid accountability for people who are actually looking — a daily loop of
          time, tailored applications, skills, and outreach, plus a weekly number that
          either counts or resets the streak.{" "}
          <strong className="font-medium text-foreground">0penings</strong> is the free
          employer-direct job board inside Cadence. Apply goes to the employer. The job
          search fails on discipline, not information.
        </p>
      </article>
    </Section>
  );
}

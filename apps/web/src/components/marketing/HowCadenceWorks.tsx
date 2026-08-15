import { Section, Stagger, StaggerItem } from "@/components/PageEnter";
import { HOW_STEPS } from "@/data/marketing";

export function HowCadenceWorks() {
  return (
    <Section id="how" delay={0.1} className="marketing-defer scroll-mt-20">
      <div className="micro text-primary">How Cadence works</div>
      <h2 className="mt-2 max-w-2xl text-3xl tracking-tight md:text-5xl">
        A week you can finish.
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground md:text-base">
        Pick a track. Run the day. Log the apply. Hit the number. That is the whole
        product.
      </p>
      <Stagger className="mt-10 grid gap-3 md:grid-cols-2">
        {HOW_STEPS.map((step) => (
          <StaggerItem key={step.n}>
            <article className="flex h-full flex-col gap-3 rounded-lg bg-card px-5 py-6 ring-1 ring-border">
              <div className="micro text-primary">{step.n}</div>
              <h3 className="text-xl tracking-tight">{step.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </article>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

import { Link } from "react-router-dom";
import { Section } from "@/components/PageEnter";
import { Button } from "@/components/ui/button";

export function FinalCta() {
  return (
    <Section delay={0.2} className="marketing-defer">
      <div className="rounded-lg px-6 py-12 ring-1 ring-border md:px-10 md:py-16">
        <div className="micro text-primary">Start</div>
        <h2 className="mt-3 max-w-2xl text-3xl tracking-tight md:text-6xl">
          Stay in the hunt.
        </h2>
        <p className="mt-4 max-w-lg text-base leading-relaxed text-muted-foreground">
          Pick a track. Run the day. Apply on the employer site. Hit the week.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild>
            <Link to="/me">Start Cadence</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/jobs">Browse 0penings</Link>
          </Button>
        </div>
      </div>
    </Section>
  );
}

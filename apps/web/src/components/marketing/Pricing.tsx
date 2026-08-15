import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Section, Stagger, StaggerItem } from "@/components/PageEnter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  PLANS,
  detectRegion,
  writeRegionParam,
  type Region,
} from "@/data/marketing";
import { cn } from "@/lib/utils";

export function Pricing() {
  const [region, setRegion] = useState<Region>("world");

  useEffect(() => {
    setRegion(detectRegion());
  }, []);

  const onRegion = (value: string) => {
    if (value !== "world" && value !== "in") return;
    setRegion(value);
    writeRegionParam(value);
  };

  return (
    <Section id="pricing" delay={0.16} className="marketing-defer scroll-mt-20">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="micro text-primary">Pricing</div>
          <h2 className="mt-2 max-w-xl text-3xl tracking-tight md:text-5xl">
            Cadence is paid. 0penings is free.
          </h2>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground md:text-base">
            Worldwide and India prices. Yearly is Most used. Start the loop on this
            device.
          </p>
        </div>
        <ToggleGroup
          type="single"
          value={region}
          onValueChange={onRegion}
          variant="outline"
          spacing={0}
          aria-label="Pricing region"
        >
          <ToggleGroupItem value="world">Worldwide</ToggleGroupItem>
          <ToggleGroupItem value="in">India</ToggleGroupItem>
        </ToggleGroup>
      </div>

      <Stagger className="mt-10 grid gap-3 md:grid-cols-3">
        {PLANS.map((plan) => {
          const price = plan[region];
          return (
            <StaggerItem key={plan.id}>
              <article
                className={cn(
                  "flex h-full flex-col gap-5 rounded-lg bg-card px-5 py-6 ring-1 ring-border",
                  plan.featured && "ring-primary",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="micro text-primary">{plan.name}</div>
                  {plan.badge ? <Badge>{plan.badge}</Badge> : null}
                </div>
                <div>
                  <div className="font-display text-4xl tracking-tight">
                    {price.amount}
                    <span className="text-lg text-muted-foreground">{price.period}</span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{plan.cadence}</p>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">{price.note}</p>
                <Button asChild className="mt-auto" variant={plan.featured ? "default" : "outline"}>
                  <Link to="/me">Start Cadence</Link>
                </Button>
              </article>
            </StaggerItem>
          );
        })}
      </Stagger>
    </Section>
  );
}

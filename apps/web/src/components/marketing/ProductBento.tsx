import { Link } from "react-router-dom";
import { Section, Stagger, StaggerItem } from "@/components/PageEnter";
import { Badge } from "@/components/ui/badge";
import { COUNTRIES, COUNTRY_META } from "@/data/countries";
import { BENTO } from "@/data/marketing";

const RINGS = [
  { label: "Time" },
  { label: "Apps" },
  { label: "Skills" },
  { label: "Outreach" },
] as const;

export function ProductBento() {
  return (
    <Section id="product" delay={0.12} className="marketing-defer scroll-mt-20">
      <div className="micro text-primary">Product</div>
      <h2 className="mt-2 max-w-2xl text-3xl tracking-tight md:text-5xl">
        Cadence holds the week. 0penings finds the role.
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground md:text-base">
        The same chrome as the app. No live job fetch on this page.
      </p>
      <Stagger className="mt-10 grid gap-3 md:grid-cols-6">
        {BENTO.map((tile) => (
          <StaggerItem key={tile.id} className={tile.span}>
            <article className="flex h-full flex-col gap-4 rounded-lg bg-card px-5 py-6 ring-1 ring-border">
              <div>
                <div className="micro text-primary">{tile.kicker}</div>
                <h3 className="mt-2 text-xl tracking-tight">{tile.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{tile.body}</p>
              </div>
              {tile.id === "cadence" ? <CadencePreview /> : null}
              {tile.id === "rings" ? <RingsPreview /> : null}
              {tile.id === "board" ? <BoardPreview /> : null}
              {tile.id === "markets" ? <MarketsPreview /> : null}
            </article>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

function CadencePreview() {
  return (
    <dl className="mt-auto grid grid-cols-3 gap-2 font-mono text-sm tabular-nums">
      <div className="rounded-md px-3 py-2 ring-1 ring-border">
        <dt className="micro">Check-in</dt>
        <dd className="mt-1 text-foreground">Daily</dd>
      </div>
      <div className="rounded-md px-3 py-2 ring-1 ring-border">
        <dt className="micro">Week</dt>
        <dd className="mt-1 text-foreground">Hit / miss</dd>
      </div>
      <div className="rounded-md px-3 py-2 ring-1 ring-border">
        <dt className="micro">Streak</dt>
        <dd className="mt-1 text-foreground">Resets</dd>
      </div>
    </dl>
  );
}

function RingsPreview() {
  return (
    <ul className="mt-auto grid grid-cols-4 gap-2">
      {RINGS.map((ring) => (
        <li key={ring.label} className="flex flex-col items-center gap-2">
          <span
            aria-hidden
            className="size-12 rounded-full ring-2 ring-border ring-inset"
          />
          <span className="micro text-center">{ring.label}</span>
        </li>
      ))}
    </ul>
  );
}

function BoardPreview() {
  return (
    <div className="mt-auto overflow-hidden rounded-md ring-1 ring-border">
      <div className="grid grid-cols-[1fr_auto] gap-3 border-b px-3 py-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        <span>Role</span>
        <span>Apply</span>
      </div>
      <div className="flex flex-col gap-0 px-3 py-3 text-sm text-muted-foreground">
        <p>Title and company on the board. Apply opens the employer.</p>
        <Link to="/jobs" className="mt-2 text-primary underline-offset-4 hover:underline">
          Open 0penings
        </Link>
      </div>
    </div>
  );
}

function MarketsPreview() {
  return (
    <div className="mt-auto flex flex-wrap gap-1.5">
      {COUNTRIES.map((c) => (
        <Badge key={c} variant="outline" className="h-6 px-2 text-[11px] font-normal">
          <span>{COUNTRY_META[c].flag}</span>
          {c}
        </Badge>
      ))}
    </div>
  );
}

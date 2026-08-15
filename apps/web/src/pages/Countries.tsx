import { Link } from "react-router-dom";
import { PageEnter, Stagger, StaggerItem } from "@/components/PageEnter";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { COUNTRIES, COUNTRY_META } from "@/data/countries";
import { formatCount } from "@/lib/format";
import { useJobs } from "@/lib/useJobs";

export function Countries() {
  const { data } = useJobs(true);
  const counts = data?.by_country ?? {};
  const remote = data?.by_remote?.remote ?? 0;

  return (
    <PageEnter>
      <PageHeader
        eyebrow="Coverage"
        title="Countries"
        description={`Remote first, then on-site in the cities that hire. ${formatCount(remote)} remote listings in this month's collection.`}
      />
      <Stagger className="grid gap-3 sm:grid-cols-2">
        {COUNTRIES.map((c) => (
          <StaggerItem key={c}>
          <Link to={`/countries/${COUNTRY_META[c].slug}`}>
            <Card className="lift h-full transition-colors hover:bg-muted/40">
              <CardHeader>
                <div className="text-lg">{COUNTRY_META[c].flag}</div>
                <CardTitle>{c}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{COUNTRY_META[c].blurb}</p>
                <div className="mt-3 text-xs text-muted-foreground">
                  {formatCount(counts[c] ?? 0)} openings
                </div>
              </CardContent>
            </Card>
          </Link>
          </StaggerItem>
        ))}
      </Stagger>
    </PageEnter>
  );
}


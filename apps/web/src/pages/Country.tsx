import { Link, Navigate, useParams } from "react-router-dom";
import { JobTable } from "@/components/JobTable";
import { PageEnter, Section } from "@/components/PageEnter";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { COUNTRY_META, countryFromSlug } from "@/data/countries";
import { formatCount } from "@/lib/format";
import { useJobs } from "@/lib/useJobs";

export function Country() {
  const { slug = "" } = useParams();
  const country = countryFromSlug(slug);
  const { data, loading } = useJobs(true);
  if (!country) return <Navigate to="/countries" replace />;

  const meta = COUNTRY_META[country];
  const jobs = (data?.jobs ?? []).filter((j) => j.country === country);
  const remote = jobs.filter((j) => j.remote).length;
  const preview = jobs.slice(0, 12);

  return (
    <PageEnter>
      <p className="mb-4 text-xs text-muted-foreground">
        <Link to="/countries" className="hover:text-foreground">
          Countries
        </Link>
        {" / "}
        {country}
      </p>
      <PageHeader
        eyebrow={`${meta.flag} ${country}`}
        title={country}
        description={meta.blurb}
        actions={
          <>
            <Button asChild>
              <Link to={`/jobs?country=${encodeURIComponent(country)}`}>Open in the board</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to={`/jobs?country=${encodeURIComponent(country)}&work=remote`}>
                Remote only
              </Link>
            </Button>
          </>
        }
      />
      <p className="mb-4 text-sm text-muted-foreground">
        {loading
          ? "Counting listings…"
          : `${formatCount(jobs.length)} in this country · ${formatCount(remote)} remote`}
      </p>
      <Section delay={0.06}>
      <JobTable jobs={preview} empty={loading ? "Loading…" : "No roles for this market in the slice."} />
      {jobs.length > preview.length ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Showing 12 of {formatCount(jobs.length)}.{" "}
          <Link
            to={`/jobs?country=${encodeURIComponent(country)}`}
            className="text-foreground underline-offset-4 hover:underline"
          >
            See the rest with filters.
          </Link>
        </p>
      ) : null}
      </Section>
    </PageEnter>
  );
}

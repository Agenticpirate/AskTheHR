import { Link, Navigate, useParams } from "react-router-dom";
import { JobCard } from "../components/JobCard";
import { COUNTRY_META, countryFromSlug } from "../data/countries";
import { useJobs } from "../lib/useJobs";

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
    <>
      <p className="notice">
        <Link to="/countries">Countries</Link> / {country}
      </p>
      <div className="eyebrow">{meta.flag} {country}</div>
      <h1>{country} roles this August</h1>
      <p className="lede">{meta.blurb}</p>
      <p className="notice">
        {loading
          ? "Counting listings…"
          : `${jobs.length.toLocaleString()} in this country · ${remote.toLocaleString()} remote`}
      </p>
      <div className="btn-row" style={{ margin: "18px 0 28px" }}>
        <Link className="btn btn-primary" to={`/jobs?country=${encodeURIComponent(country)}`}>
          Open in the board
        </Link>
        <Link className="btn btn-ghost" to={`/jobs?country=${encodeURIComponent(country)}&work=remote`}>
          Remote only
        </Link>
      </div>
      <div className="grid-jobs">
        {preview.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>
      {jobs.length > preview.length && (
        <p className="notice" style={{ marginTop: 16 }}>
          Showing 12 of {jobs.length.toLocaleString()}.{" "}
          <Link to={`/jobs?country=${encodeURIComponent(country)}`}>See the rest with filters.</Link>
        </p>
      )}
    </>
  );
}

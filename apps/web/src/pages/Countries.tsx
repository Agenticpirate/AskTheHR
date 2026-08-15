import { Link } from "react-router-dom";
import { COUNTRIES, COUNTRY_META } from "../data/countries";
import { useJobs } from "../lib/useJobs";

export function Countries() {
  const { data } = useJobs(true);
  const counts = data?.by_country ?? {};
  const remote = data?.by_remote?.remote ?? 0;

  return (
    <>
      <div className="eyebrow">Coverage</div>
      <h1>Ten markets we actually cover</h1>
      <p className="lede">
        Remote first, then on-site in the cities that hire. Worldwide-eligible roles sit in a
        separate bucket ({remote.toLocaleString()} remote listings in this month's collection).
      </p>
      <div className="country-grid" style={{ marginTop: 24 }}>
        {COUNTRIES.map((c) => (
          <Link key={c} className="country-card" to={`/countries/${COUNTRY_META[c].slug}`}>
            <div className="flag">{COUNTRY_META[c].flag}</div>
            <h3>{c}</h3>
            <p className="notice" style={{ margin: 0 }}>
              {COUNTRY_META[c].blurb}
            </p>
            <div className="count-line">{(counts[c] ?? 0).toLocaleString()} openings</div>
          </Link>
        ))}
      </div>
    </>
  );
}

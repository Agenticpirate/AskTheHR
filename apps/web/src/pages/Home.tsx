import { Link } from "react-router-dom";
import { AccountabilityWidget } from "../components/AccountabilityWidget";
import { JobCard } from "../components/JobCard";
import { COUNTRIES, COUNTRY_META } from "../data/countries";
import { featuredRemote } from "../lib/jobs";
import { useJobs } from "../lib/useJobs";

export function Home() {
  const { data, error, loading } = useJobs(false);
  const jobs = data?.jobs ?? [];
  const featured = featuredRemote(jobs, 8);
  const counts = data?.by_country ?? {};
  const total = data?.total ?? 0;
  const remote = data?.by_remote?.remote ?? featured.length;

  return (
    <>
      <section className="hero">
        <div className="hero-grid">
          <div>
            <div className="eyebrow">August 2026 · remote-first</div>
            <h1>Apply with intent. Track the week.</h1>
            <div className="rule" />
            <p className="lede">
              0pening is a job board for people who are actually looking — openings posted this
              month across ten countries, plus a weekly application target that lives on your
              device. No account. No feed. Just the work.
            </p>
            <div className="btn-row" style={{ marginTop: 22 }}>
              <Link className="btn btn-primary" to="/jobs?work=remote">
                Browse remote jobs
              </Link>
              <Link className="btn btn-ghost" to="/me">
                Set my weekly target
              </Link>
            </div>
            <p className="notice" style={{ marginTop: 16 }}>
              {loading
                ? "Loading August openings…"
                : error
                  ? "Job feed unavailable right now."
                  : `${total.toLocaleString()} openings collected · ${remote.toLocaleString()} remote · showing the freshest first.`}
            </p>
          </div>
          <AccountabilityWidget compact />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Where you can work</div>
            <h2>Ten countries, remote first</h2>
          </div>
          <Link to="/countries" className="btn btn-ghost">
            All countries
          </Link>
        </div>
        <div className="chips">
          {COUNTRIES.map((c) => (
            <Link key={c} className="chip" to={`/countries/${COUNTRY_META[c].slug}`}>
              <span>{COUNTRY_META[c].flag}</span>
              {c}
              <b>{(counts[c] ?? 0).toLocaleString()}</b>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Featured</div>
            <h2>Remote roles posted this month</h2>
          </div>
          <Link to="/jobs?work=remote" className="btn btn-ghost">
            See all remote
          </Link>
        </div>
        {featured.length === 0 && !loading ? (
          <div className="empty">No remote roles in the first slice yet.</div>
        ) : (
          <div className="grid-jobs">
            {featured.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <div className="eyebrow">How it works</div>
            <h2>A board, a target, a streak</h2>
          </div>
        </div>
        <div className="steps">
          <div className="step">
            <div className="num">01</div>
            <h3>Pick a weekly number</h3>
            <p className="notice">
              Eight applications is the default. Change it on My week. The header keeps the count
              in front of you.
            </p>
          </div>
          <div className="step">
            <div className="num">02</div>
            <h3>Apply from the listing</h3>
            <p className="notice">
              Every role links out to the employer. Hit “I applied” and it lands in your log —
              title, company, date.
            </p>
          </div>
          <div className="step">
            <div className="num">03</div>
            <h3>Protect the streak</h3>
            <p className="notice">
              Hit the target and the week counts. Miss it and the streak resets. Simple on
              purpose, so you cannot negotiate with it.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}

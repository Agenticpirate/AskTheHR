import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { JobCard } from "../components/JobCard";
import { COUNTRIES } from "../data/countries";
import { matchesFilters, type JobFilters } from "../lib/jobs";
import { useJobs } from "../lib/useJobs";

const PAGE = 20;

function readFilters(sp: URLSearchParams): JobFilters {
  const work = sp.get("work");
  return {
    q: sp.get("q") ?? "",
    country: sp.get("country") ?? "",
    place: sp.get("place") ?? "",
    work: work === "remote" || work === "onsite" ? work : "all",
  };
}

export function Jobs() {
  const { data, error, loading, loadingMore } = useJobs(true);
  const [sp, setSp] = useSearchParams();
  const filters = readFilters(sp);
  const page = Math.max(1, Number(sp.get("page") || 1) || 1);

  const set = (patch: Record<string, string>) => {
    const next = new URLSearchParams(sp);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in patch)) next.delete("page");
    setSp(next, { replace: true });
  };

  const jobs = data?.jobs ?? [];
  const filtered = useMemo(
    () => jobs.filter((j) => matchesFilters(j, filters)),
    [jobs, filters.q, filters.country, filters.place, filters.work],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const safePage = Math.min(page, pages);
  const slice = filtered.slice((safePage - 1) * PAGE, safePage * PAGE);

  return (
    <>
      <div className="eyebrow">Job board</div>
      <h1>Openings posted this August</h1>
      <p className="lede">
        Search title or company, then narrow by country, city or state, and remote vs on-site.
        {data
          ? ` ${data.shown.toLocaleString()} listings in this build${data.shown < data.total ? ` of ${data.total.toLocaleString()} collected` : ""}.`
          : ""}
      </p>

      <form className="filters" onSubmit={(e) => e.preventDefault()} style={{ marginTop: 22 }}>
        <div className="field">
          <label htmlFor="q">Search</label>
          <input
            id="q"
            value={filters.q}
            placeholder="Engineer, nurse, Stripe…"
            onChange={(e) => set({ q: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="country">Country</label>
          <select
            id="country"
            value={filters.country}
            onChange={(e) => set({ country: e.target.value })}
          >
            <option value="">All countries</option>
            {COUNTRIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
            <option value="worldwide">Worldwide / unspecified</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="place">State or city</label>
          <input
            id="place"
            value={filters.place}
            placeholder="Bengaluru, Ontario, Berlin"
            onChange={(e) => set({ place: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="work">Work style</label>
          <select
            id="work"
            value={filters.work}
            onChange={(e) => set({ work: e.target.value })}
          >
            <option value="all">Remote + on-site</option>
            <option value="remote">Remote only</option>
            <option value="onsite">On-site only</option>
          </select>
        </div>
        <div className="field">
          <label>&nbsp;</label>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => set({ q: "", country: "", place: "", work: "" })}
          >
            Reset
          </button>
        </div>
      </form>

      <div className="results-bar">
        <span>
          {loading
            ? "Loading…"
            : `${filtered.length.toLocaleString()} roles`}
          {loadingMore ? " · loading the rest of the board…" : ""}
        </span>
        <span>
          Page {safePage} of {pages}
        </span>
      </div>

      {error && <div className="empty">{error}</div>}
      {!error && !loading && slice.length === 0 && (
        <div className="empty">Nothing matches those filters. Try a wider country or search.</div>
      )}
      <div className="grid-jobs">
        {slice.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>
      {pages > 1 && (
        <div className="pager">
          <button type="button" disabled={safePage <= 1} onClick={() => set({ page: String(safePage - 1) })}>
            Prev
          </button>
          <span>
            {safePage} / {pages}
          </span>
          <button
            type="button"
            disabled={safePage >= pages}
            onClick={() => set({ page: String(safePage + 1) })}
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}

import { COUNTRIES, type Country } from "../data/countries";

export type Job = {
  id: string;
  title: string;
  company: string;
  country: string;
  state: string;
  city: string;
  remote: boolean;
  url: string;
  posted_at: string | null;
  source: string;
  description: string;
};

export type JobsPayload = {
  generated_at: string;
  month: string;
  total: number;
  shown: number;
  primary: number;
  more: boolean;
  more_count: number;
  jobs: Job[];
  by_remote?: { remote: number; onsite: number } | null;
  by_country?: Record<string, number> | null;
  by_source?: Record<string, number> | null;
};

export type JobFilters = {
  q: string;
  country: string;
  place: string;
  work: "all" | "remote" | "onsite";
};

let primaryCache: Promise<JobsPayload> | null = null;
let allCache: Promise<JobsPayload> | null = null;

export function loadJobs(): Promise<JobsPayload> {
  if (!primaryCache) {
    primaryCache = fetch("/jobs.json")
      .then((r) => {
        if (!r.ok) throw new Error(`jobs.json ${r.status}`);
        return r.json() as Promise<JobsPayload>;
      })
      .catch((err) => {
        primaryCache = null;
        throw err;
      });
  }
  return primaryCache;
}

export function loadAllJobs(): Promise<JobsPayload> {
  if (!allCache) {
    allCache = loadJobs().then(async (primary) => {
      if (!primary.more) return primary;
      try {
        const extra = await fetch("/jobs-more.json");
        if (!extra.ok) return primary;
        const body = (await extra.json()) as { jobs: Job[] };
        return { ...primary, jobs: primary.jobs.concat(body.jobs || []) };
      } catch {
        return primary;
      }
    });
  }
  return allCache;
}

export function jobPath(job: Job): string {
  return `/jobs/${encodeURIComponent(job.id)}`;
}

export function locationLabel(job: Job): string {
  const parts = [job.city, job.state, job.country].filter(Boolean);
  if (job.remote && parts.length === 0) return "Remote · Worldwide";
  if (job.remote && !job.city && !job.state && job.country) {
    return `Remote · ${job.country}`;
  }
  if (job.remote) return `Remote · ${parts.join(", ")}`;
  return parts.join(", ") || "Location not listed";
}

export function matchesFilters(job: Job, f: JobFilters): boolean {
  if (f.work === "remote" && !job.remote) return false;
  if (f.work === "onsite" && job.remote) return false;
  if (f.country === "worldwide") {
    if (job.country) return false;
  } else if (f.country && job.country !== f.country) {
    return false;
  }
  if (f.place) {
    const needle = f.place.trim().toLowerCase();
    const hay = `${job.city} ${job.state}`.toLowerCase();
    if (!hay.includes(needle)) return false;
  }
  if (f.q) {
    const needle = f.q.trim().toLowerCase();
    const hay =
      `${job.title} ${job.company} ${job.description} ${job.city} ${job.state} ${job.country}`.toLowerCase();
    if (!hay.includes(needle)) return false;
  }
  return true;
}

export function countryCounts(jobs: Job[]): Record<string, number> {
  const out: Record<string, number> = { worldwide: 0 };
  for (const c of COUNTRIES) out[c] = 0;
  for (const j of jobs) {
    if (j.country && j.country in out) out[j.country] += 1;
    else out.worldwide += 1;
  }
  return out;
}

export function featuredRemote(jobs: Job[], n = 8): Job[] {
  return jobs.filter((j) => j.remote && j.title && j.company).slice(0, n);
}

export function similarJobs(jobs: Job[], job: Job, n = 4): Job[] {
  return jobs
    .filter((j) => j.id !== job.id)
    .map((j) => {
      let s = 0;
      if (j.remote === job.remote) s += 1;
      if (j.country && j.country === job.country) s += 2;
      const words = new Set(
        job.title
          .toLowerCase()
          .split(/\W+/)
          .filter((w) => w.length > 3),
      );
      for (const w of j.title.toLowerCase().split(/\W+/)) {
        if (words.has(w)) s += 2;
      }
      return { j, s };
    })
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, n)
    .map((x) => x.j);
}

export function isCountry(v: string): v is Country {
  return (COUNTRIES as readonly string[]).includes(v);
}

export function findJob(jobs: Job[], id: string): Job | undefined {
  return jobs.find((j) => j.id === id);
}

/** Job boards we may ingest from, but never send the seeker to apply. */
const AGGREGATOR_MARKERS = [
  "himalayas.app",
  "remoteok.com",
  "remotive.com",
  "weworkremotely.com",
  "jobicy.com",
  "workingnomads",
  "remotefirstjobs",
  "arbeitnow",
  "themuse.com",
  "europa.eu",
  "jobsyn.org",
  "linkedin.com",
  "indeed.com",
  "glassdoor",
  "naukri",
  "instahyre",
  "internshala",
  "remotejobs.org",
  "arbeitsagentur.de",
  "mycareersfuture",
  "jobsuche",
];

/** True when the apply URL is an employer ATS or company career site. */
export function isEmployerApplyUrl(url: string): boolean {
  if (!url) return false;
  try {
    const host = new URL(url).hostname.toLowerCase();
    if (!host) return false;
    return !AGGREGATOR_MARKERS.some((m) => host.includes(m));
  } catch {
    return false;
  }
}

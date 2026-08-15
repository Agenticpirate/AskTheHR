# 0pening

Premium job dashboard plus weekly application accountability.
Static Vite + React + TypeScript for Cloudflare Pages (not Vercel).

August 2026 openings across USA, India, Canada, UK, Australia, Germany, Netherlands, Ireland, Singapore, and France.

## Pages

- `/` Home: KPI cards, country chips, featured remote roles
- `/jobs` Board: search, country, city, remote vs on-site, pagination
- `/jobs/:id` Detail: external apply and I applied
- `/me` Accountability: nickname, weekly target, streak, application log
- `/countries` Ten markets
- `/countries/:slug` Country slice

## Scripts

    npm install
    npm run dev
    npm run build
    npm run preview

The build script typechecks and writes the production bundle to dist/.

## Cloudflare Pages

| Setting | Value |
|---|---|
| Framework preset | None (or Vite) |
| Build command | npm run build |
| Build output directory | dist |
| Node version | 20+ |

If this folder is not the repo root, set Pages root directory to apps/web.

wrangler.toml sets pages_build_output_dir = dist.

    npx wrangler pages deploy dist --project-name 0pening

SPA fallback is public/_redirects: /* /index.html 200

## Job data

- public/jobs.json — up to 3000 India-eligible remote roles whose apply URL is the employer (ATS or company career site)
- payload.total is the employer-URL eligible count, not a job-board scrape total
- Aggregators (Himalayas, Jobsyn, EURES, …) are discovery sources only — Apply never goes there

Refresh from the collector:

    python3 scripts/ingest_jobs.py

## Accountability

src/lib/tracker.ts uses a TrackerStore. MVP is localStorage (seeker.tracker.v1).
Swap the store for a Cloudflare KV or D1 worker later. The React hook does not care.

Product name is 0pening. AskTheHR is the brand behind it.

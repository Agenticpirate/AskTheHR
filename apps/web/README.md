# 0pening

Remote-first job board plus weekly application accountability.
Static Vite + React + TypeScript for Cloudflare Pages (not Vercel).

August 2026 openings across USA, India, Canada, UK, Australia, Germany, Netherlands, Ireland, Singapore, and France.

## Pages

- `/` Home: hero, weekly target widget, country chips, featured remote jobs
- `/jobs` Board: search, country, state/city, remote vs on-site, pagination
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

- public/jobs.json — first 3000 remote-first rows plus totals (total vs shown / primary)
- public/jobs-more.json — remaining rows, lazy-loaded by the board

Refresh from the collector:

    python3 scripts/ingest_jobs.py

Source of truth: /workspace/jobs/remote-aug2026.jsonl and /workspace/jobs/summary.json

## Accountability

src/lib/tracker.ts uses a TrackerStore. MVP is localStorage (seeker.tracker.v1).
Swap the store for a Cloudflare KV or D1 worker later. The React hook does not care.

Product name is 0pening in index.html and src/components/Layout.tsx.

0pening is the product. AskTheHR is the marketing brand (askthehr.com).

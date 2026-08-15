# 0pening

Premium job dashboard plus weekly application accountability.
Static Vite + React + TypeScript for Cloudflare Pages (not Vercel).

August 2026 openings across USA, India, Canada, UK, Australia, Germany, Netherlands, Ireland, Singapore, and France.

## Pages

- `/` Home: KPI cards, country chips, featured remote roles
- `/jobs` Board: search, country, city, remote vs on-site, pagination
- `/jobs/:id` Detail: external apply and I applied
- `/me` Accountability: nickname, weekly target, application log, reminders
- `/streak` Achievements: daily/weekly streak, badges, XP, heatmap, share, reminders
- `/board` Public opt-in leaderboard
- `/countries` Ten markets
- `/countries/:slug` Country slice
- `/join` Claim a 0pening name (local profile + `/api/username`)
- `/terms` Short terms: usernames, trademark reclaim, employer apply links

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

## Reminders

Browser notifications are free. A client scheduler fires once per day while the tab is open (default 09:00 Asia/Calcutta).

After the tab is closed, Web Push via Cloudflare is the free unlimited path.

## Theme

Header sun/moon cycles light, dark, then system. Persisted as localStorage 0pening.theme. The dark class is applied on html.

## Paid messaging

WhatsApp reminders require profile.plan = paid. POST /api/remind rejects free plans, never sends when enabled is false, and returns 501 whatsapp_not_configured when Cloud API env is missing. Free users keep browser reminders. Messaging turns off when the plan ends.

## Usernames

`/join` claims a handle (3–20, letter first, `[a-z0-9_]`). Reserved brands and
public-figure lookalikes live in `src/data/reserved-usernames.ts` and always
win. POST `/api/username` stores claims in the `USERNAMES` KV binding, or
in-memory when the binding is missing. A username is a license — 0pening may
reclaim it after a trademark or impersonation complaint.


# 0pening

**0pening** is a remote-first job board with a weekly application target. It is built by **AskTheHR**.

- Product: [0pening.com](https://0pening.com)
- Marketing: [askthehr.com](https://askthehr.com)

The name is **0pening** (digit zero). It is not Opening.

## What it is

A static board of current openings plus a private accountability loop. Browse roles, apply on the employer site, then log the application so the week stays honest. No account. No feed. The target and log stay on the device until auth ships.

Coverage is ten countries: USA, India, Canada, UK, Australia, Germany, Netherlands, Ireland, Singapore, and France. Remote listings are first.

## Product surface

| Path | Purpose |
|---|---|
| `/` | Home, featured remote roles, weekly target |
| `/jobs` | Search and filters |
| `/jobs/:id` | Role detail and apply |
| `/me` | Weekly target, streak, application log |
| `/countries` | Ten markets |
| `/countries/:slug` | Country slice |

## Hosting

Cloudflare Pages serves the Vite React TypeScript app.

See apps/web for Pages settings.

Root directory: apps/web. Command: npm run build. Output directory: dist.

## Repo layout

apps/web is the Pages app. data/scripts holds collectors. docs holds product notes.

apps/web/public/jobs.json is the published job slice. Raw collector dumps are not in this repo.

## License

MIT. Copyright (c) 2026 AskTheHR / 0pening.


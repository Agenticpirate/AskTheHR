# 0pening product

0pening (digit zero) is the product. AskTheHR is the marketing brand.

## Promise

A job dashboard for people who are actually looking, plus a weekly application target that lives on the device. Openings posted this month across ten countries. No account. No feed.

## Markets

USA, India, Canada, UK, Australia, Germany, Netherlands, Ireland, Singapore, France. Remote-first; on-site and hybrid remain filterable.

## Surfaces

- Marketing `/`: AskTheHR company page. Cadence is paid accountability. 0penings is the free employer-direct board inside Cadence.
- App home `/app`: KPI cards, country chips, featured remote roles
- Jobs: search, country, state/city, remote vs on-site, pagination
- Job detail: outbound apply, I applied log
- My week: nickname, weekly target (default 8), application log, reminders
- Streak: daily/weekly streak, badges, XP, heatmap, share
- Countries: ten-market index and per-country slice
- Join: claim a 0pening name (license, not property)
- Terms: usernames, reserved names, trademark reclaim, employer apply links

## Accountability

The tracker is a TrackerStore. MVP persistence is localStorage (seeker.tracker.v1). Hit the weekly number and the week counts. Miss it and the streak resets.

## Stack

Vite + React + TypeScript + Tailwind + shadcn/ui. Static host is Cloudflare Pages. App directory apps/web. Output dist. Not Vercel.

## Brand rules

- AskTheHR is the company.
- Cadence is paid accountability.
- 0penings (leading zero) is the free employer-direct job board inside Cadence. Never write Opening.
- App chrome still says 0pening for the workspace.

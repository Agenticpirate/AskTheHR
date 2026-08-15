# Job sources

0pening publishes a remote-first slice of August 2026 openings for ten countries. Collectors and normalizers live in data/scripts/. The site ingest lives in apps/web/scripts/ingest_jobs.py.

Raw dumps and jsonl files are not committed. The published board is apps/web/public/jobs.json (first about 3000 remote-first rows plus totals).

## Public boards and aggregators

- Himalayas (country browse and search)
- EURES
- Bundesagentur fuer Arbeit / Jobsuche (Germany)
- MyCareersFuture (Singapore)
- Remote-first boards folded in normalize: Remote OK, Remotive, Jobicy, We Work Remotely, Working Nomads, RemoteJobs.org, Remote First Jobs
- ATS company career pages (pull_ats.py)
- City-gap backfills for under-covered markets

## Pipeline

1. Collect per source into local raw dumps (outside this repo).
2. Normalize, infer country/remote, and fold (normalize.py, fold_new_and_infer.py, combine.py).
3. Ingest a capped public JSON for the static app (apps/web/scripts/ingest_jobs.py to public/jobs.json).

Each listing keeps title, company, country, city/state, remote flag, apply URL, posted date, source, and a short description. Apply always goes to the employer or source URL.

## Ten-country target

USA, India, Canada, UK, Australia, Germany, Netherlands, Ireland, Singapore, France.

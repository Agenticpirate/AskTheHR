#!/usr/bin/env python3
"""Build public/jobs.json from India-eligible remote jobs with employer apply URLs.

Aggregators (Himalayas, Jobsyn, EURES, RemoteOK, …) are discovery sources.
Apply must go to the employer ATS or company career site. Source may stay
"himalayas" when the url was rewritten to the employer.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

NORM = Path("/workspace/jobs/normalized")
OUT_DIR = Path(__file__).resolve().parents[1] / "public"
PRIMARY_CAP = 3000
TARGET = {
    "USA", "India", "Canada", "UK", "Australia",
    "Germany", "Netherlands", "Ireland", "Singapore", "France",
}

ATS_MARKERS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "workable.com",
    "icims.com",
    "taleo.net",
    "successfactors",
    "breezy.hr",
    "darwinbox",
    "recruitee.com",
    "jobvite.com",
)

AGGREGATOR_MARKERS = (
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
)

APPLY_KEYS = (
    "url",
    "apply_url",
    "applicationUrl",
    "application_url",
    "applicationLink",
    "applyUrl",
    "applyurl",
    "canonical",
    "canonical_url",
    "canonicalUrl",
)

# Prefer ATS dumps, then standalone boards, then eligible (employer-url rows only).
SOURCE_FILES = [
    (0, "ats-global-remote.jsonl", "ats"),
    (1, "ats-india-more.jsonl", "ats"),
    (2, "ats-india.jsonl", "ats"),
    (3, "greenhouse.jsonl", "board_ats"),
    (4, "lever.jsonl", "board_ats"),
    (5, "ashby.jsonl", "board_ats"),
    (6, "india-eligible-remote.jsonl", "eligible"),
]


def host_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def norm_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        p = urlparse(raw)
    except Exception:
        return raw.rstrip("/")
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path or ""
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]
    scheme = (p.scheme or "https").lower()
    return urlunparse((scheme, host, path, "", p.query, ""))


def is_aggregator_host(host: str) -> bool:
    h = (host or "").lower()
    if h.startswith("www."):
        h = h[4:]
    return any(m in h for m in AGGREGATOR_MARKERS)


def is_ats_host(host: str) -> bool:
    return any(m in (host or "").lower() for m in ATS_MARKERS)


def is_company_career_host(host: str) -> bool:
    h = (host or "").lower()
    if h.startswith("www."):
        h = h[4:]
    if not h or is_aggregator_host(h):
        return False
    first = h.split(".")[0]
    if first in {"careers", "jobs", "job", "jobs2"}:
        return True
    return "careers" in h


def is_employer_apply_url(url: str) -> bool:
    host = host_of(url)
    if not host or is_aggregator_host(host):
        return False
    return True


def pick_employer_url(row: dict) -> str:
    """Prefer an employer apply URL on the record. Source may stay the board."""
    for key in APPLY_KEYS:
        val = row.get(key)
        if isinstance(val, str) and is_employer_apply_url(val.strip()):
            return val.strip()
    return ""


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def clean(o: dict, apply_url: str) -> dict | None:
    url = (apply_url or "").strip()
    title = (o.get("title") or "").strip()
    if not url or not title or not is_employer_apply_url(url):
        return None
    country = (o.get("country") or "").strip()
    if country and country not in TARGET:
        country = ""
    posted = o.get("posted_at")
    if posted is not None:
        posted = str(posted).strip() or None
    desc = o.get("description") or ""
    if isinstance(desc, str):
        desc = " ".join(desc.split())
        if len(desc) > 900:
            desc = desc[:897].rstrip() + "..."
    else:
        desc = ""
    jid = str(o.get("id") or "").strip() or f"url:{abs(hash(url))}"
    return {
        "id": jid,
        "title": title[:200],
        "company": (o.get("company") or "").strip()[:120] or "Unknown company",
        "country": country,
        "state": (o.get("state") or "").strip()[:80],
        "city": (o.get("city") or "").strip()[:80],
        "remote": bool(o.get("remote")),
        "url": url,
        "posted_at": posted,
        "source": (o.get("source") or "unknown").strip()[:40],
        "description": desc,
    }


def richer(a: dict, b: dict) -> dict:
    def score(o: dict) -> tuple:
        desc = o.get("description") or ""
        return (
            1 if o.get("posted_at") else 0,
            1 if o.get("country") == "India" else 0,
            1 if o.get("country") in TARGET else 0,
            1 if o.get("remote") else 0,
            len(desc),
            1 if o.get("city") else 0,
        )
    return a if score(a) >= score(b) else b


def rank(o: dict, source_pri: int) -> tuple:
    posted = o.get("posted_at") or ""
    aug = 1 if str(posted).startswith("2026-08") else 0
    host = host_of(o["url"])
    return (
        10 - source_pri,
        1 if is_ats_host(host) else 0,
        1 if is_company_career_host(host) else 0,
        1 if o.get("country") == "India" else 0,
        1 if o.get("remote") else 0,
        aug,
        posted or "",
        1 if o.get("description") else 0,
    )


def accept_row(row: dict, kind: str) -> bool:
    if kind == "ats":
        return True
    if kind == "board_ats":
        if not row.get("remote"):
            return False
        return (row.get("country") or "").strip() in {"", "India"}
    return True


def country_slice(counts: Counter) -> dict[str, int]:
    return {k: int(counts.get(k) or 0) for k in TARGET}


def main() -> None:
    kept: dict[str, tuple[tuple, dict]] = {}
    raw_n = 0
    skipped_agg = 0

    for source_pri, name, kind in SOURCE_FILES:
        path = NORM / name
        if not path.exists():
            continue
        for row in iter_jsonl(path):
            raw_n += 1
            if not accept_row(row, kind):
                continue
            apply_url = pick_employer_url(row)
            if not apply_url:
                skipped_agg += 1
                continue
            c = clean(row, apply_url)
            if not c:
                continue
            key = norm_url(c["url"])
            if not key:
                continue
            r = rank(c, source_pri)
            if key in kept:
                old_r, old = kept[key]
                kept[key] = (max(r, old_r), richer(c, old))
            else:
                kept[key] = (r, c)

    ranked = sorted(kept.values(), key=lambda x: x[0], reverse=True)
    corpus = [j for _, j in ranked]
    primary = corpus[:PRIMARY_CAP]

    by_source: Counter = Counter()
    by_country: Counter = Counter()
    remote_n = 0
    onsite_n = 0
    for j in corpus:
        by_source[j["source"] or "unknown"] += 1
        if j["country"]:
            by_country[j["country"]] += 1
        if j["remote"]:
            remote_n += 1
        else:
            onsite_n += 1

    total = len(corpus)
    shown = len(primary)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "month": "2026-08",
        "total": total,
        "shown": shown,
        "primary": shown,
        "more": False,
        "more_count": 0,
        "by_remote": {"remote": remote_n, "onsite": onsite_n},
        "by_country": country_slice(by_country),
        "by_source": dict(by_source.most_common()),
    }
    payload = {**meta, "jobs": primary}
    out = OUT_DIR / "jobs.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    more_p = OUT_DIR / "jobs-more.json"
    if more_p.exists():
        more_p.unlink()

    hosts = Counter(host_of(j["url"]) for j in primary)
    print(
        f"raw={raw_n} employer_corpus={total} shown={shown} "
        f"skipped_no_employer_url={skipped_agg}"
    )
    print("top_hosts", hosts.most_common(15))
    print("jobs.json", out.stat().st_size, "->", out)


if __name__ == "__main__":
    main()

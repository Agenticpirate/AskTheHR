#!/usr/bin/env python3
"""Build public/jobs.json — employer ATS / careers Apply URLs only.

Aggregators (Himalayas, RemoteOK, EURES, Jobsyn, …) are discovery sources.
A job with only an aggregator URL is dropped. Source labels never name a
third-party job portal.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

NORM = Path("/workspace/jobs/normalized")
COMBINED = Path("/workspace/jobs/remote-aug2026.jsonl")
OUT_DIR = Path(__file__).resolve().parents[1] / "public"
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

# Locked: never as Apply, never as source branding.
AGGREGATOR_MARKERS = (
    "himalayas.app",
    "himalayas.com",
    "remoteok.com",
    "remoteok.io",
    "remotive.com",
    "remotive.io",
    "weworkremotely.com",
    "jobicy.com",
    "workingnomads.com",
    "workingnomads.co",
    "workingnomads",
    "arbeitnow.com",
    "arbeitnow",
    "themuse.com",
    "europa.eu",
    "de.jobsyn.org",
    "jobsyn.org",
    "linkedin.com",
    "indeed.com",
    "naukri.com",
    "instahyre.com",
    "internshala.com",
    "wellfound.com",
    "angel.co",
    "glassdoor.com",
    "ziprecruiter.com",
    "simplyhired.com",
    "dice.com",
    "monster.com",
    "careerbuilder.com",
    "remotefirstjobs",
    "remotejobs.org",
    "arbeitsagentur.de",
    "mycareersfuture",
    "jobsuche",
    "nodesk.co",
    "nodesk.com",
)

AGGREGATOR_SOURCE_NAMES = {
    "himalayas",
    "remoteok",
    "remotive",
    "weworkremotely",
    "jobicy",
    "workingnomads",
    "arbeitnow",
    "themuse",
    "eures",
    "jobsyn",
    "directemployers",
    "linkedin",
    "indeed",
    "naukri",
    "instahyre",
    "internshala",
    "wellfound",
    "angellist",
    "angel",
    "glassdoor",
    "ziprecruiter",
    "simplyhired",
    "dice",
    "monster",
    "careerbuilder",
    "remotefirstjobs",
    "remotejobsorg",
    "nodesk",
    "jobdata",
    "mycareersfuture",
    "mcf",
    "jobsuche",
    "ba-jobsuche",
    "nycopendata",
    "chronicle",
    "actjobs",
}

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

# Prefer Fortune 500 / ATS, then boards, then the combined remote dump.
SOURCE_FILES = [
    (0, NORM / "fortune500-aug2026.jsonl", "f500"),
    (1, NORM / "ats-global-remote.jsonl", "ats"),
    (2, NORM / "ats-india-more.jsonl", "ats"),
    (3, NORM / "ats-india.jsonl", "ats"),
    (4, NORM / "greenhouse.jsonl", "board_ats"),
    (5, NORM / "lever.jsonl", "board_ats"),
    (6, NORM / "ashby.jsonl", "board_ats"),
    (7, NORM / "india-eligible-remote.jsonl", "eligible"),
    (8, COMBINED, "combined"),
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
    """Employer ATS / careers URL only. Aggregator-only rows return empty."""
    for key in APPLY_KEYS:
        val = row.get(key)
        if isinstance(val, str) and is_employer_apply_url(val.strip()):
            return val.strip()
    return ""


def ats_source_from_host(host: str) -> str:
    h = (host or "").lower()
    mapping = (
        ("greenhouse", "greenhouse.io"),
        ("lever", "lever.co"),
        ("ashby", "ashbyhq.com"),
        ("workday", "myworkdayjobs.com"),
        ("smartrecruiters", "smartrecruiters.com"),
        ("workable", "workable.com"),
        ("icims", "icims.com"),
        ("taleo", "taleo.net"),
        ("successfactors", "successfactors"),
        ("breezy", "breezy.hr"),
        ("darwinbox", "darwinbox"),
        ("recruitee", "recruitee.com"),
        ("jobvite", "jobvite.com"),
    )
    for name, marker in mapping:
        if marker in h:
            return name
    if is_company_career_host(h):
        return "employer"
    return "employer"


def public_source(row_source: str, url: str) -> str:
    src = (row_source or "").strip().lower()
    if not src or src in AGGREGATOR_SOURCE_NAMES or src == "unknown":
        return ats_source_from_host(host_of(url))
    if src in {"greenhouse", "lever", "ashby", "workday", "smartrecruiters"}:
        return src
    # Keep other ATS-ish names; never a portal brand.
    if any(m in src for m in AGGREGATOR_SOURCE_NAMES):
        return ats_source_from_host(host_of(url))
    return src[:40]


def public_id(jid: str, url: str) -> str:
    raw = (jid or "").strip()
    low = raw.lower()
    prefix = raw.split(":", 1)[0].lower()
    branded = prefix in AGGREGATOR_SOURCE_NAMES or any(
        token in low
        for token in (
            "himalayas",
            "remoteok",
            "remotive",
            "jobicy",
            "arbeitnow",
            "weworkremotely",
            "workingnomads",
            "themuse",
            "eures",
            "jobsyn",
            "linkedin",
            "indeed",
            "naukri",
        )
    )
    if not raw or branded:
        digest = hashlib.sha1(norm_url(url).encode("utf-8")).hexdigest()[:16]
        return f"job:{digest}"
    return raw[:200]


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
    return {
        "id": public_id(str(o.get("id") or ""), url),
        "title": title[:200],
        "company": (o.get("company") or "").strip()[:120] or "Unknown company",
        "country": country,
        "state": (o.get("state") or "").strip()[:80],
        "city": (o.get("city") or "").strip()[:80],
        "remote": bool(o.get("remote")),
        "url": url,
        "posted_at": posted,
        "source": public_source(str(o.get("source") or ""), url),
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
        1 if o.get("remote") else 0,
        10 - source_pri,
        1 if is_ats_host(host) else 0,
        1 if is_company_career_host(host) else 0,
        1 if o.get("country") == "India" else 0,
        1 if o.get("country") in TARGET else 0,
        aug,
        posted or "",
        1 if o.get("description") else 0,
    )


def accept_row(row: dict, kind: str) -> bool:
    if kind in {"ats", "f500"}:
        return True
    if kind == "board_ats":
        return bool(row.get("remote"))
    if kind == "combined":
        return bool(row.get("remote"))
    return True


def country_slice(counts: Counter) -> dict[str, int]:
    return {k: int(counts.get(k) or 0) for k in TARGET}


def main() -> None:
    kept: dict[str, tuple[tuple, dict]] = {}
    raw_n = 0
    skipped_agg = 0

    for source_pri, path, kind in SOURCE_FILES:
        if not path.exists():
            print("skip missing", path)
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
    primary = corpus

    leaked = [j for j in primary if not is_employer_apply_url(j["url"])]
    if leaked:
        raise SystemExit(f"aggregator Apply URLs leaked: {len(leaked)}")

    by_source: Counter = Counter()
    by_country: Counter = Counter()
    remote_n = 0
    onsite_n = 0
    for j in corpus:
        by_source[j["source"] or "employer"] += 1
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
    branded = sum(1 for j in primary if j["source"] in AGGREGATOR_SOURCE_NAMES)
    print(
        f"raw={raw_n} employer_corpus={total} shown={shown} "
        f"skipped_no_employer_url={skipped_agg} aggregator_apply=0 "
        f"aggregator_source_labels={branded}"
    )
    print("top_hosts", hosts.most_common(15))
    print("by_source_shown", Counter(j["source"] for j in primary).most_common())
    print("jobs.json", out.stat().st_size, "->", out)


if __name__ == "__main__":
    main()

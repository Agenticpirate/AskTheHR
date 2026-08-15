#!/usr/bin/env python3
"""Himalayas country SEARCH collector. Does not touch browse himalayas_p*.json files."""
from __future__ import annotations

import fcntl
import html
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")
JSONL = NORM / "himalayas.jsonl"
LOG = RAW / "himalayas_country_log.txt"
COMBINE = Path("/workspace/jobs/scripts/combine.py")
BASE = "https://himalayas.app/jobs/api/search"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"

# India first (must finish), then thin ingest, then the rest
COUNTRY_ORDER = ["IN", "NL", "FR", "SG", "AU", "IE", "GB", "CA", "DE", "US"]
COUNTRY_NAME = {
    "IN": "India",
    "US": "USA",
    "GB": "UK",
    "NL": "Netherlands",
    "FR": "France",
    "SG": "Singapore",
    "AU": "Australia",
    "IE": "Ireland",
    "CA": "Canada",
    "DE": "Germany",
}

# light city/state hints from locationRestrictions
CITY_HINTS = {
    "bengaluru": ("Karnataka", "Bengaluru"),
    "bangalore": ("Karnataka", "Bengaluru"),
    "hyderabad": ("Telangana", "Hyderabad"),
    "mumbai": ("Maharashtra", "Mumbai"),
    "delhi": ("Delhi", "Delhi"),
    "new delhi": ("Delhi", "New Delhi"),
    "pune": ("Maharashtra", "Pune"),
    "chennai": ("Tamil Nadu", "Chennai"),
    "gurgaon": ("Haryana", "Gurugram"),
    "gurugram": ("Haryana", "Gurugram"),
    "noida": ("Uttar Pradesh", "Noida"),
    "kolkata": ("West Bengal", "Kolkata"),
    "ahmedabad": ("Gujarat", "Ahmedabad"),
    "toronto": ("Ontario", "Toronto"),
    "vancouver": ("British Columbia", "Vancouver"),
    "montreal": ("Quebec", "Montreal"),
    "montréal": ("Quebec", "Montreal"),
    "ottawa": ("Ontario", "Ottawa"),
    "calgary": ("Alberta", "Calgary"),
    "london": ("", "London"),
    "manchester": ("", "Manchester"),
    "dublin": ("", "Dublin"),
    "amsterdam": ("", "Amsterdam"),
    "paris": ("", "Paris"),
    "berlin": ("Berlin", "Berlin"),
    "munich": ("Bavaria", "Munich"),
    "sydney": ("New South Wales", "Sydney"),
    "melbourne": ("Victoria", "Melbourne"),
    "singapore": ("", "Singapore"),
    "new york": ("New York", "New York"),
    "san francisco": ("California", "San Francisco"),
    "seattle": ("Washington", "Seattle"),
    "austin": ("Texas", "Austin"),
    "boston": ("Massachusetts", "Boston"),
    "chicago": ("Illinois", "Chicago"),
}

TIMEBOX_SEC = 15 * 60
SLEEP_MIN, SLEEP_MAX = 0.120, 0.250


def log(msg: str) -> None:
    line = msg if msg.endswith("\n") else msg + "\n"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
    print(line, end="", flush=True)


def strip_html(text) -> str:
    if not text:
        return ""
    s = html.unescape(str(text))
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def short_desc(text, n=400) -> str:
    s = strip_html(text)
    return s if len(s) <= n else s[:n].rstrip()


def posted_iso(pub) -> str:
    if pub is None or pub == "":
        return ""
    try:
        n = int(pub)
    except (TypeError, ValueError):
        return str(pub)
    if n > 10**12:
        n //= 1000
    if n <= 0:
        return ""
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OverflowError, OSError, ValueError):
        return ""


def job_url(j: dict) -> str:
    for key in ("applicationLink", "guid"):
        u = (j.get(key) or "").strip()
        if u:
            return u
    slug = (j.get("companySlug") or "").strip()
    title = (j.get("title") or "").strip()
    if slug and title:
        s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return f"https://himalayas.app/companies/{slug}/jobs/{s}"
    return ""


def job_id(j: dict, url: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = [p for p in path.split("/") if p]
    if "jobs" in parts:
        i = parts.index("jobs")
        if i + 1 < len(parts):
            slug = parts[i + 1]
            if i >= 1:
                return f"himalayas:{parts[i - 1]}/{slug}"
            return f"himalayas:{slug}"
    if parts:
        return f"himalayas:{parts[-1]}"
    guid = (j.get("guid") or "").strip()
    if guid:
        return f"himalayas:{guid.rstrip('/').split('/')[-1]}"
    return f"himalayas:{re.sub(r'[^a-z0-9]+', '-', (j.get('title') or 'job').lower()).strip('-')}"


def company_of(j: dict) -> str:
    name = (j.get("companyName") or "").strip()
    if name.lower() in {"name", "company", ""}:
        return (j.get("companySlug") or "").strip()
    return name


def city_state(locs) -> tuple[str, str]:
    if not locs:
        return "", ""
    if isinstance(locs, str):
        locs = [locs]
    for loc in locs:
        if not loc:
            continue
        tl = str(loc).strip().lower()
        if tl in CITY_HINTS:
            st, ci = CITY_HINTS[tl]
            return st, ci
    return "", ""


def normalize_job(j: dict, iso: str) -> dict | None:
    url = job_url(j)
    if not url:
        return None
    title = strip_html(j.get("title") or "")
    if not title:
        return None
    st, ci = city_state(j.get("locationRestrictions") or [])
    return {
        "id": job_id(j, url),
        "title": title,
        "company": company_of(j),
        "country": COUNTRY_NAME[iso],
        "state": st,
        "city": ci,
        "remote": True,
        "url": url,
        "posted_at": posted_iso(j.get("pubDate")),
        "source": "himalayas",
        "description": short_desc(j.get("excerpt") or j.get("description") or ""),
    }


def fetch(url: str) -> tuple[int, dict | None, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
            status = resp.status
            try:
                return status, json.loads(raw.decode("utf-8")), ""
            except json.JSONDecodeError as e:
                return status, None, f"json: {e}"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return e.code, None, body
    except Exception as e:
        return 0, None, f"{type(e).__name__}: {e}"


def fetch_retry(url: str) -> tuple[int, dict | None, str]:
    status, data, err = fetch(url)
    if status == 429:
        time.sleep(3)
        status, data, err = fetch(url)
    return status, data, err


def existing_pages(cc: str) -> set[int]:
    pages = set()
    prefix = f"himalayas_{cc.lower()}_p"
    for p in RAW.glob(f"{prefix}*.json"):
        m = re.fullmatch(rf"himalayas_{cc.lower()}_p(\d+)\.json", p.name)
        if m:
            pages.add(int(m.group(1)))
    return pages


def load_seen_urls() -> set[str]:
    seen: set[str] = set()
    if not JSONL.exists():
        return seen
    with JSONL.open("r", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
        try:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                u = (obj.get("url") or "").strip()
                if u:
                    seen.add(u)
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    return seen


def append_jsonl(rows: list[dict], seen: set[str]) -> int:
    if not rows:
        return 0
    JSONL.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with JSONL.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            # re-scan tail safety: reload seen from current file if empty
            if not seen and JSONL.stat().st_size:
                fh.seek(0)
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    u = (obj.get("url") or "").strip()
                    if u:
                        seen.add(u)
                fh.seek(0, 2)
            for row in rows:
                u = row.get("url") or ""
                if not u or u in seen:
                    continue
                seen.add(u)
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
                added += 1
            fh.flush()
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    return added


def normalize_files(cc: str, pages: list[int], seen: set[str]) -> int:
    rows = []
    for n in pages:
        path = RAW / f"himalayas_{cc.lower()}_p{n}.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        jobs = data.get("jobs") or []
        for j in jobs:
            if not isinstance(j, dict):
                continue
            rec = normalize_job(j, cc)
            if rec:
                rows.append(rec)
    return append_jsonl(rows, seen)


def run_combine(tag: str) -> dict:
    import subprocess
    r = subprocess.run(
        [sys.executable, str(COMBINE)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    out = (r.stdout or "") + (r.stderr or "")
    log(f"# combine {tag} exit={r.returncode}\n{out.strip()}")
    summary = {}
    sp = Path("/workspace/jobs/summary.json")
    if sp.exists():
        try:
            summary = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return summary


def crawl_country(iso: str, seen: set[str], deadline: float, must_finish: bool) -> dict:
    cc = iso.lower()
    stats = {
        "iso": iso,
        "country": COUNTRY_NAME[iso],
        "totalCount": None,
        "pages_fetched": 0,
        "pages_skipped": 0,
        "jobs_raw": 0,
        "jobs_written": 0,
        "complete": False,
        "errors": [],
        "stop_reason": "",
    }
    have = existing_pages(cc)
    page = 1
    pending_pages: list[int] = []
    empty_streak = 0
    advertised = None

    while True:
        if (not must_finish) and time.time() >= deadline:
            stats["stop_reason"] = "timebox"
            break

        url = f"{BASE}?{urlencode({'country': iso, 'page': page})}"
        path = RAW / f"himalayas_{cc}_p{page}.json"

        if page in have and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                jobs = data.get("jobs") or []
                total = data.get("totalCount")
                offset = data.get("offset", (page - 1) * 20)
                n = len(jobs)
                if advertised is None and total is not None:
                    advertised = int(total)
                    stats["totalCount"] = advertised
                log(f"{iso}\t{page}\t200\t{n}\t{total}\tskip-exists")
                stats["pages_skipped"] += 1
                pending_pages.append(page)
                if n == 0:
                    empty_streak += 1
                    if empty_streak >= 2:
                        stats["complete"] = True
                        stats["stop_reason"] = "empty"
                        break
                else:
                    empty_streak = 0
                    stats["jobs_raw"] += n
                if advertised and isinstance(offset, int) and offset + n >= advertised and n < 20:
                    stats["complete"] = True
                    stats["stop_reason"] = "reached-total"
                    break
                if advertised and page * 20 >= advertised and n == 0:
                    stats["complete"] = True
                    stats["stop_reason"] = "past-total"
                    break
                page += 1
                continue
            except Exception:
                pass

        status, data, err = fetch_retry(url)
        n = 0
        total = None
        if data and isinstance(data, dict):
            jobs = data.get("jobs") or []
            n = len(jobs) if isinstance(jobs, list) else 0
            total = data.get("totalCount")
            if advertised is None and total is not None:
                advertised = int(total)
                stats["totalCount"] = advertised
            # atomic-ish write
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
            stats["pages_fetched"] += 1
            stats["jobs_raw"] += n
            pending_pages.append(page)
            have.add(page)
        else:
            stats["errors"].append(f"page={page} status={status} err={err[:120]}")

        log(f"{iso}\t{page}\t{status}\t{n}\t{total}")

        if status != 200 or data is None:
            # retry already done; skip this page and stop if repeated failure
            stats["stop_reason"] = f"http {status}"
            if status in (403, 401):
                break
            # try next page once more after a pause
            time.sleep(1.0)
            page += 1
            if len(stats["errors"]) >= 5:
                break
            continue

        if n == 0:
            empty_streak += 1
            if empty_streak >= 1:
                stats["complete"] = True
                stats["stop_reason"] = "empty"
                break
        else:
            empty_streak = 0

        offset = data.get("offset")
        if advertised is not None and isinstance(offset, int) and offset + n >= advertised:
            stats["complete"] = True
            stats["stop_reason"] = "reached-total"
            break

        page += 1
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

        if pending_pages and len(pending_pages) >= 50:
            written = normalize_files(iso, pending_pages, seen)
            stats["jobs_written"] += written
            log(f"# normalize {iso} pages {pending_pages[0]}-{pending_pages[-1]} wrote={written} seen={len(seen)}")
            pending_pages = []

    if pending_pages:
        written = normalize_files(iso, pending_pages, seen)
        stats["jobs_written"] += written
        log(f"# normalize {iso} final pages wrote={written} seen={len(seen)}")

    # if we skipped/resumed, also normalize any pages we have on disk for this country
    # (already done incrementally)

    if stats["totalCount"] and stats["jobs_raw"] >= stats["totalCount"]:
        stats["complete"] = True
        if not stats["stop_reason"]:
            stats["stop_reason"] = "raw>=total"

    return stats


def probe(iso: str) -> dict:
    url = f"{BASE}?{urlencode({'country': iso, 'page': 1})}"
    status, data, err = fetch_retry(url)
    info = {"iso": iso, "status": status, "err": err, "totalCount": None, "n": 0, "offset": None, "limit": None}
    if data:
        info["totalCount"] = data.get("totalCount")
        info["n"] = len(data.get("jobs") or [])
        info["offset"] = data.get("offset")
        info["limit"] = data.get("limit")
    log(f"# probe {iso} status={status} n={info['n']} totalCount={info['totalCount']} offset={info['offset']} limit={info['limit']}")
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
    return info


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    start = time.time()
    deadline = start + TIMEBOX_SEC
    log(f"# start {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} endpoint={BASE}")
    log("# probe first: IN, IN+exclude_worldwide, US")

    # explicit probes requested
    for extra in (
        f"{BASE}?country=IN&page=1",
        f"{BASE}?country=IN&exclude_worldwide=true&page=1",
        f"{BASE}?country=US&page=1",
    ):
        status, data, err = fetch_retry(extra)
        n = len((data or {}).get("jobs") or []) if data else 0
        total = (data or {}).get("totalCount") if data else None
        offset = (data or {}).get("offset") if data else None
        limit = (data or {}).get("limit") if data else None
        log(f"# probe-url {extra} status={status} n={n} totalCount={total} offset={offset} limit={limit} err={err[:80] if err else ''}")
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

    probes = {}
    for iso in COUNTRY_ORDER:
        probes[iso] = probe(iso)

    seen = load_seen_urls()
    log(f"# existing himalayas.jsonl unique urls={len(seen)}")

    all_stats = []
    india_summary = None

    for iso in COUNTRY_ORDER:
        must = iso == "IN"
        if (not must) and time.time() >= deadline:
            log(f"# skip {iso} timebox")
            all_stats.append({
                "iso": iso, "country": COUNTRY_NAME[iso], "totalCount": (probes.get(iso) or {}).get("totalCount"),
                "pages_fetched": 0, "jobs_raw": 0, "jobs_written": 0, "complete": False,
                "errors": [], "stop_reason": "timebox-before-start",
            })
            continue
        log(f"# crawl {iso} must_finish={must} remaining={max(0, deadline-time.time()):.0f}s")
        st = crawl_country(iso, seen, deadline, must_finish=must)
        all_stats.append(st)
        log(f"# done {iso} fetched={st['pages_fetched']} skipped={st['pages_skipped']} raw={st['jobs_raw']} written={st['jobs_written']} complete={st['complete']} reason={st['stop_reason']} errors={len(st['errors'])}")
        if iso == "IN":
            india_summary = run_combine("after-india")

    end_summary = run_combine("final")
    elapsed = time.time() - start
    report = {
        "elapsed_sec": round(elapsed, 1),
        "probes": probes,
        "countries": all_stats,
        "combine_after_india": {
            "total": (india_summary or {}).get("total"),
            "by_source": (india_summary or {}).get("by_source"),
            "by_country": (india_summary or {}).get("by_country"),
        } if india_summary else None,
        "combine_final": {
            "total": end_summary.get("total"),
            "by_source": end_summary.get("by_source"),
            "by_country": end_summary.get("by_country"),
        },
        "jsonl_unique": len(seen),
    }
    (RAW / "himalayas_country_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(f"# finished elapsed={elapsed:.1f}s jsonl_unique={len(seen)}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

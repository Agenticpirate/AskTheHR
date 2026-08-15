#!/usr/bin/env python3
"""Continue Himalayas BROWSE pagination. Resume-safe, noclobber, 12-min timebox.

GET https://himalayas.app/jobs/api?limit=20&offset=N
Filename himalayas_p{page}.json maps to offset = 300 + (page-1)*20
(p1 was offset 300; p2448 is offset 49240).

Never overwrites existing files (O_EXCL / noclobber).
429 -> wait 60s. Sleep 150-250ms between requests.

If merging, appends new unique URLs into remote-aug2026.jsonl only
(does NOT rewrite/replace ingest; does not drop mcf/eures/jobsuche).
"""
from __future__ import annotations

import fcntl
import html
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path("/workspace/jobs")
RAW = ROOT / "raw"
COMBINED = ROOT / "remote-aug2026.jsonl"
LOG = RAW / "himalayas_browse_pull_log.txt"
REPORT = RAW / "himalayas_browse_pull_report.json"

BASE = "https://himalayas.app/jobs/api"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
LIMIT = 20
OFFSET_BASE = 300  # himalayas_p1.json == offset 300
TIMEBOX_SEC = 12 * 60
SLEEP_MIN = 0.150
SLEEP_MAX = 0.250
WAIT_429 = 60
PAGE_RX = re.compile(r"^himalayas_p(\d+)\.json$")

COUNTRY_ALIASES = {
    "united states of america": "USA",
    "united states": "USA",
    "u.s.a.": "USA",
    "u.s.": "USA",
    "usa": "USA",
    "us": "USA",
    "america": "USA",
    "united kingdom": "UK",
    "great britain": "UK",
    "england": "UK",
    "scotland": "UK",
    "wales": "UK",
    "northern ireland": "UK",
    "britain": "UK",
    "u.k.": "UK",
    "uk": "UK",
    "gb": "UK",
    "india": "India",
    "bharat": "India",
    "canada": "Canada",
    "australia": "Australia",
    "germany": "Germany",
    "deutschland": "Germany",
    "netherlands": "Netherlands",
    "the netherlands": "Netherlands",
    "holland": "Netherlands",
    "ireland": "Ireland",
    "republic of ireland": "Ireland",
    "singapore": "Singapore",
    "france": "France",
}

CITY_HINTS = {
    "bengaluru": ("India", "Karnataka", "Bengaluru"),
    "bangalore": ("India", "Karnataka", "Bengaluru"),
    "hyderabad": ("India", "Telangana", "Hyderabad"),
    "mumbai": ("India", "Maharashtra", "Mumbai"),
    "delhi": ("India", "Delhi", "Delhi"),
    "new delhi": ("India", "Delhi", "New Delhi"),
    "pune": ("India", "Maharashtra", "Pune"),
    "chennai": ("India", "Tamil Nadu", "Chennai"),
    "gurgaon": ("India", "Haryana", "Gurugram"),
    "gurugram": ("India", "Haryana", "Gurugram"),
    "noida": ("India", "Uttar Pradesh", "Noida"),
    "kolkata": ("India", "West Bengal", "Kolkata"),
    "ahmedabad": ("India", "Gujarat", "Ahmedabad"),
    "toronto": ("Canada", "Ontario", "Toronto"),
    "vancouver": ("Canada", "British Columbia", "Vancouver"),
    "montreal": ("Canada", "Quebec", "Montreal"),
    "montréal": ("Canada", "Quebec", "Montreal"),
    "ottawa": ("Canada", "Ontario", "Ottawa"),
    "calgary": ("Canada", "Alberta", "Calgary"),
    "london": ("UK", "", "London"),
    "manchester": ("UK", "", "Manchester"),
    "dublin": ("Ireland", "", "Dublin"),
    "sydney": ("Australia", "New South Wales", "Sydney"),
    "melbourne": ("Australia", "Victoria", "Melbourne"),
    "berlin": ("Germany", "Berlin", "Berlin"),
    "munich": ("Germany", "Bavaria", "Munich"),
    "amsterdam": ("Netherlands", "", "Amsterdam"),
    "paris": ("France", "", "Paris"),
    "singapore": ("Singapore", "", "Singapore"),
    "new york": ("USA", "New York", "New York"),
    "san francisco": ("USA", "California", "San Francisco"),
    "seattle": ("USA", "Washington", "Seattle"),
    "austin": ("USA", "Texas", "Austin"),
    "boston": ("USA", "Massachusetts", "Boston"),
    "chicago": ("USA", "Illinois", "Chicago"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def page_to_offset(page: int) -> int:
    return OFFSET_BASE + (page - 1) * LIMIT


def existing_pages() -> list[int]:
    nums: list[int] = []
    if not RAW.exists():
        return nums
    for fn in os.listdir(RAW):
        m = PAGE_RX.fullmatch(fn)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def max_page() -> int:
    ps = existing_pages()
    return max(ps) if ps else 0


def page_path(page: int) -> Path:
    return RAW / f"himalayas_p{page}.json"


def save_exclusive(path: Path, raw: bytes) -> bool:
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)
    return True


def fetch(url: str) -> tuple[int, bytes]:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=45) as resp:
            return resp.getcode(), resp.read()
    except HTTPError as e:
        body = b""
        try:
            body = e.read()
        except Exception:
            pass
        return e.code, body
    except (URLError, Exception) as e:
        return 0, str(e).encode()


def fetch_retry(url: str, deadline: float) -> tuple[int, bytes]:
    status, body = fetch(url)
    retries = 0
    while status == 429 and retries < 4:
        retries += 1
        remain = deadline - time.time()
        if remain <= 1:
            return status, body
        wait = min(WAIT_429, max(1.0, remain - 1))
        log(f"429 wait {wait:.0f}s retry={retries} url={url}")
        time.sleep(wait)
        if time.time() >= deadline:
            return status, body
        status, body = fetch(url)
    return status, body


def strip_html(text) -> str:
    if not text:
        return ""
    s = html.unescape(str(text))
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def posted_date(pub) -> str:
    if pub is None or pub == "":
        return ""
    try:
        n = int(pub)
    except (TypeError, ValueError):
        s = str(pub)
        return s[:10] if len(s) >= 10 and s[4] == "-" else s
    if n > 10**12:
        n //= 1000
    if n <= 0:
        return ""
    try:
        return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%d")
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


def job_id(url: str, title: str) -> str:
    path = urlparse(url).path.strip("/")
    parts = [p for p in path.split("/") if p]
    if parts:
        return f"himalayas:{parts[-1]}"
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "job").lower()).strip("-")
    return f"himalayas:{slug}"


def company_of(j: dict) -> str:
    name = (j.get("companyName") or "").strip()
    if name.lower() in {"name", "company", ""}:
        slug = (j.get("companySlug") or "").strip()
        return slug.replace("-", " ").title() if slug else name
    return name


def loc_tuple(locs) -> tuple[str, str, str]:
    if not locs:
        return "", "", ""
    if isinstance(locs, str):
        locs = [locs]
    country = state = city = ""
    for loc in locs:
        if not loc:
            continue
        tl = str(loc).strip().lower()
        if tl in CITY_HINTS:
            return CITY_HINTS[tl]
        if tl in COUNTRY_ALIASES and not country:
            country = COUNTRY_ALIASES[tl]
            continue
        # "City, Country" / "City, State, Country"
        bits = [b.strip() for b in str(loc).split(",") if b.strip()]
        if len(bits) >= 2:
            last = bits[-1].lower()
            if last in COUNTRY_ALIASES:
                country = country or COUNTRY_ALIASES[last]
                if len(bits) == 2:
                    city = city or bits[0]
                else:
                    city = city or bits[0]
                    state = state or bits[1]
            elif bits[0].lower() in CITY_HINTS:
                return CITY_HINTS[bits[0].lower()]
        elif tl in COUNTRY_ALIASES:
            country = country or COUNTRY_ALIASES[tl]
    return country, state, city


def normalize_job(j: dict) -> dict | None:
    url = job_url(j)
    if not url:
        return None
    title = strip_html(j.get("title") or "")
    if not title:
        return None
    country, state, city = loc_tuple(j.get("locationRestrictions") or [])
    desc = strip_html(j.get("excerpt") or j.get("description") or "")
    if len(desc) > 400:
        desc = desc[:400].rstrip()
    return {
        "id": job_id(url, title),
        "title": title,
        "company": company_of(j),
        "country": country,
        "state": state,
        "city": city,
        "remote": True,
        "url": url,
        "posted_at": posted_date(j.get("pubDate")),
        "source": "himalayas",
        "description": desc,
    }


def load_seen_urls() -> set[str]:
    seen: set[str] = set()
    if not COMBINED.exists():
        return seen
    with COMBINED.open("r", encoding="utf-8") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
        except OSError:
            pass
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
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    return seen


def append_jsonl(rows: list[dict], seen: set[str]) -> int:
    if not rows:
        return 0
    added = 0
    with COMBINED.open("a+", encoding="utf-8") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except OSError:
            pass
        try:
            for row in rows:
                u = (row.get("url") or "").strip()
                if not u or u in seen:
                    continue
                seen.add(u)
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
                added += 1
            fh.flush()
        finally:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    return added


def normalize_page_file(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        return []
    out: list[dict] = []
    for j in jobs:
        if isinstance(j, dict):
            rec = normalize_job(j)
            if rec:
                out.append(rec)
    return out


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    start = time.time()
    deadline = start + TIMEBOX_SEC

    disk_max = max_page()
    start_page = disk_max + 1
    start_offset = page_to_offset(start_page)
    log(
        f"START browse disk_max=p{disk_max} start_page={start_page} "
        f"start_offset={start_offset} timebox={TIMEBOX_SEC}s "
        f"formula=300+(N-1)*20"
    )

    pages_written: list[int] = []
    pages_skipped = 0
    last_offset = None
    last_page = None
    last_total = None
    last_njobs = None
    errors: list[str] = []
    stop_reason = ""
    empty_streak = 0

    page = start_page
    while True:
        if time.time() >= deadline:
            stop_reason = "timebox"
            break

        # Always hop to current disk max+1 so we don't fight other writers
        # on the same page number, but still fill if we already claimed one.
        live_max = max_page()
        if live_max + 1 > page:
            page = live_max + 1

        path = page_path(page)
        if path.exists():
            pages_skipped += 1
            page += 1
            continue

        offset = page_to_offset(page)
        url = f"{BASE}?limit={LIMIT}&offset={offset}"
        status, body = fetch_retry(url, deadline)

        if status != 200:
            errors.append(f"page={page} offset={offset} status={status}")
            log(f"ERR page={page} offset={offset} status={status}")
            if status == 429:
                stop_reason = "429"
                break
            if status in (403, 401):
                stop_reason = f"http {status}"
                break
            empty_streak += 1
            if empty_streak >= 3:
                stop_reason = "errors"
                break
            time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
            continue

        try:
            data = json.loads(body)
        except Exception as e:
            errors.append(f"page={page} json {e}")
            log(f"ERR page={page} bad json")
            stop_reason = "bad-json"
            break

        jobs = data.get("jobs") or []
        n = len(jobs) if isinstance(jobs, list) else 0
        total = data.get("totalCount")
        if total is not None:
            try:
                last_total = int(total)
            except (TypeError, ValueError):
                pass
        last_njobs = n

        if not save_exclusive(path, body):
            pages_skipped += 1
            log(f"SKIP exists page={page} offset={offset}")
            page += 1
            time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))
            continue

        pages_written.append(page)
        last_page = page
        last_offset = offset
        log(
            f"OK page={page} offset={offset} jobs={n} totalCount={data.get('totalCount')} "
            f"saved={path.name}"
        )

        if n == 0:
            empty_streak += 1
            if empty_streak >= 2:
                stop_reason = "empty"
                break
        else:
            empty_streak = 0

        if isinstance(last_total, int) and offset + n >= last_total:
            stop_reason = "reached-total"
            break

        page += 1
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

    if not stop_reason:
        stop_reason = "timebox"

    # MERGE by URL into existing remote-aug2026.jsonl (append-only, no replace)
    merged = 0
    seen_n = 0
    if pages_written:
        log(f"MERGE start pages={len(pages_written)} into {COMBINED.name} by URL")
        seen = load_seen_urls()
        seen_n = len(seen)
        rows: list[dict] = []
        for p in pages_written:
            rows.extend(normalize_page_file(page_path(p)))
        merged = append_jsonl(rows, seen)
        log(f"MERGE wrote={merged} candidates={len(rows)} seen_before={seen_n} seen_after={len(seen)}")

    disk_after = existing_pages()
    disk_max_after = max(disk_after) if disk_after else 0
    last_off = last_offset if last_offset is not None else (
        page_to_offset(disk_max_after) if disk_max_after else None
    )
    remaining = None
    if isinstance(last_total, int) and last_off is not None:
        remaining = max(0, last_total - (last_off + (last_njobs or 0)))

    elapsed = time.time() - start
    report = {
        "elapsed_sec": round(elapsed, 1),
        "disk_max_before": disk_max,
        "start_page": start_page,
        "start_offset": start_offset,
        "pages_written": len(pages_written),
        "pages_written_range": (
            [pages_written[0], pages_written[-1]] if pages_written else None
        ),
        "pages_skipped": pages_skipped,
        "last_page": last_page,
        "last_offset": last_off,
        "last_njobs": last_njobs,
        "totalCount": last_total,
        "remaining": remaining,
        "disk_max_after": disk_max_after,
        "disk_count_after": len(disk_after),
        "merged_new_urls": merged,
        "stop_reason": stop_reason,
        "errors": errors[:20],
        "finished_at": now_iso(),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log("REPORT " + json.dumps(report, ensure_ascii=False))
    log(f"FINISH elapsed={elapsed:.1f}s")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

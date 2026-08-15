#!/usr/bin/env python3
"""Continue Himalayas /jobs/api/search by country. Resume-safe, 12-min timebox.

GET https://himalayas.app/jobs/api/search?country=CC&sort=recent&page=N
Saves raw/himalayas_{cc}_p{N}.json (never clobbers).
Merges into normalized/himalayas.jsonl and re-runs combine.py every ~10k new rows.
"""
from __future__ import annotations

import fcntl
import html
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")
JSONL = NORM / "himalayas.jsonl"
LOG = RAW / "himalayas_search_pull_log.txt"
COMBINE = Path("/workspace/jobs/scripts/combine.py")
BASE = "https://himalayas.app/jobs/api/search"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"

TIMEBOX_SEC = 12 * 60
SLEEP_SEC = 0.150
LIMIT = 20
COMBINE_EVERY = 10_000
WAIT_429 = 60

COUNTRY_ORDER = ["IN", "US", "CA", "GB", "AU", "IE"]
COUNTRY_NAME = {
    "IN": "India",
    "US": "USA",
    "CA": "Canada",
    "GB": "UK",
    "AU": "Australia",
    "IE": "Ireland",
}

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
    "sydney": ("New South Wales", "Sydney"),
    "melbourne": ("Victoria", "Melbourne"),
    "new york": ("New York", "New York"),
    "san francisco": ("California", "San Francisco"),
    "seattle": ("Washington", "Seattle"),
    "austin": ("Texas", "Austin"),
    "boston": ("Massachusetts", "Boston"),
    "chicago": ("Illinois", "Chicago"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def strip_html(text) -> str:
    if not text:
        return ""
    s = html.unescape(str(text))
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


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


def normalize_job(j: dict, cc: str) -> dict | None:
    url = job_url(j)
    if not url:
        return None
    title = strip_html(j.get("title") or "")
    if not title:
        return None
    st, ci = city_state(j.get("locationRestrictions") or [])
    desc = strip_html(j.get("excerpt") or j.get("description") or "")
    if len(desc) > 400:
        desc = desc[:400].rstrip()
    return {
        "id": job_id(j, url),
        "title": title,
        "company": company_of(j),
        "country": COUNTRY_NAME.get(cc, cc),
        "state": st,
        "city": ci,
        "remote": True,
        "url": url,
        "posted_at": posted_iso(j.get("pubDate")),
        "source": "himalayas",
        "description": desc,
    }


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
    while status == 429 and retries < 3:
        retries += 1
        remain = deadline - time.time()
        wait = min(WAIT_429, max(1, remain - 2))
        log(f"429 {url} wait {wait:.0f}s retry={retries}")
        if time.time() + wait >= deadline:
            time.sleep(min(wait, max(0, deadline - time.time())))
            return status, body
        time.sleep(wait)
        status, body = fetch(url)
    return status, body


def existing_pages(cc: str) -> set[int]:
    pages: set[int] = set()
    rx = re.compile(rf"^himalayas_{cc.lower()}_p(\d+)\.json$")
    if not RAW.exists():
        return pages
    for fn in os.listdir(RAW):
        m = rx.fullmatch(fn)
        if m:
            pages.add(int(m.group(1)))
    return pages


def next_page(cc: str) -> int:
    have = existing_pages(cc)
    if not have:
        return 1
    mx = max(have)
    for i in range(1, mx + 2):
        if i not in have:
            return i
    return mx + 1


def page_path(cc: str, page: int) -> Path:
    return RAW / f"himalayas_{cc.lower()}_p{page}.json"


def save_exclusive(path: Path, raw: bytes) -> bool:
    tmp = path.with_suffix(".json.tmp")
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)
    return True


def load_page(path: Path) -> dict | None:
    try:
        if not path.exists() or path.stat().st_size < 20:
            return None
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def load_seen() -> set[str]:
    seen: set[str] = set()
    if not JSONL.exists():
        return seen
    with JSONL.open("r", encoding="utf-8") as fh:
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
    JSONL.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with JSONL.open("a+", encoding="utf-8") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except OSError:
            pass
        try:
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
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    return added


def normalize_pages(cc: str, pages: list[int], seen: set[str]) -> int:
    rows: list[dict] = []
    for n in pages:
        d = load_page(page_path(cc, n))
        if not d:
            continue
        jobs = d.get("jobs") or []
        if not isinstance(jobs, list):
            continue
        for j in jobs:
            if isinstance(j, dict):
                rec = normalize_job(j, cc)
                if rec:
                    rows.append(rec)
    return append_jsonl(rows, seen)


def run_combine(tag: str) -> dict:
    log(f"COMBINE start {tag}")
    try:
        r = subprocess.run(
            [sys.executable, str(COMBINE)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        log(f"COMBINE {tag} exit={r.returncode} {out[:400]}")
    except Exception as e:
        log(f"COMBINE {tag} failed {e}")
        return {}
    sp = Path("/workspace/jobs/summary.json")
    if sp.exists():
        try:
            return json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


class Combiner:
    def __init__(self) -> None:
        self.since_combine = 0
        self.total_added = 0
        self.combines = 0

    def note(self, added: int, tag: str, force: bool = False) -> None:
        self.since_combine += added
        self.total_added += added
        if force or self.since_combine >= COMBINE_EVERY:
            run_combine(f"{tag} added={self.since_combine}")
            self.combines += 1
            self.since_combine = 0


def crawl_country(cc: str, seen: set[str], deadline: float, combiner: Combiner) -> dict:
    stats = {
        "cc": cc,
        "country": COUNTRY_NAME[cc],
        "totalCount": None,
        "start_page": None,
        "end_page": None,
        "pages_fetched": 0,
        "pages_skipped": 0,
        "jobs_raw": 0,
        "jobs_written": 0,
        "complete": False,
        "errors": [],
        "stop_reason": "",
        "disk_pages": 0,
    }
    page = next_page(cc)
    stats["start_page"] = page
    pending: list[int] = []
    empty_streak = 0
    advertised: int | None = None

    log(f"==== COUNTRY {cc} {COUNTRY_NAME[cc]} start_page={page} remaining={max(0, deadline-time.time()):.0f}s ====")

    while True:
        if time.time() >= deadline:
            stats["stop_reason"] = "timebox"
            break

        path = page_path(cc, page)
        url = f"{BASE}?{urlencode({'country': cc, 'sort': 'recent', 'page': str(page)})}"

        existing = load_page(path)
        if existing is not None:
            jobs = existing.get("jobs") or []
            n = len(jobs) if isinstance(jobs, list) else 0
            total = existing.get("totalCount")
            if advertised is None and total is not None:
                advertised = int(total)
                stats["totalCount"] = advertised
            stats["pages_skipped"] += 1
            stats["jobs_raw"] += n
            pending.append(page)
            stats["end_page"] = page
            if n == 0:
                empty_streak += 1
                if empty_streak >= 2:
                    stats["complete"] = True
                    stats["stop_reason"] = "empty"
                    break
            else:
                empty_streak = 0
            if advertised and page * LIMIT >= advertised:
                stats["complete"] = True
                stats["stop_reason"] = "reached-total"
                break
            page += 1
            continue

        status, body = fetch_retry(url, deadline)
        if status != 200:
            stats["errors"].append(f"page={page} status={status}")
            log(f"ERR {cc} page={page} status={status}")
            if status in (403, 401):
                stats["stop_reason"] = f"http {status}"
                break
            if status == 429:
                stats["stop_reason"] = "429"
                break
            empty_streak += 1
            if empty_streak >= 3:
                stats["stop_reason"] = "errors"
                break
            page += 1
            time.sleep(SLEEP_SEC)
            continue

        try:
            data = json.loads(body)
        except Exception as e:
            stats["errors"].append(f"page={page} json {e}")
            log(f"ERR {cc} page={page} bad json")
            break

        jobs = data.get("jobs") or []
        n = len(jobs) if isinstance(jobs, list) else 0
        total = data.get("totalCount")
        if advertised is None and total is not None:
            advertised = int(total)
            stats["totalCount"] = advertised

        if not save_exclusive(path, body):
            # another writer won; treat as skip
            existing = load_page(path)
            if existing:
                jobs = existing.get("jobs") or []
                n = len(jobs) if isinstance(jobs, list) else 0
            stats["pages_skipped"] += 1
        else:
            stats["pages_fetched"] += 1

        stats["jobs_raw"] += n
        pending.append(page)
        stats["end_page"] = page
        log(
            f"OK {cc} page={page} jobs={n} offset={data.get('offset')} "
            f"totalCount={data.get('totalCount')} saved={path.name}"
        )

        if n == 0:
            empty_streak += 1
            if empty_streak >= 2:
                stats["complete"] = True
                stats["stop_reason"] = "empty"
                break
        else:
            empty_streak = 0

        if advertised and page * LIMIT >= advertised:
            stats["complete"] = True
            stats["stop_reason"] = "reached-total"
            break

        page += 1
        time.sleep(SLEEP_SEC)

        if len(pending) >= 40:
            written = normalize_pages(cc, pending, seen)
            stats["jobs_written"] += written
            log(f"MERGE {cc} pages {pending[0]}-{pending[-1]} wrote={written} seen={len(seen)}")
            combiner.note(written, f"{cc}-p{pending[-1]}")
            pending = []

    if pending:
        written = normalize_pages(cc, pending, seen)
        stats["jobs_written"] += written
        log(f"MERGE {cc} final wrote={written} seen={len(seen)}")
        combiner.note(written, f"{cc}-final")

    have = existing_pages(cc)
    stats["disk_pages"] = len(have)
    stats["disk_max"] = max(have) if have else 0
    if advertised and stats["disk_pages"] * LIMIT >= advertised:
        stats["complete"] = True
        if not stats["stop_reason"] or stats["stop_reason"] == "timebox":
            stats["stop_reason"] = "disk-covers-total"
    return stats


def merge_all_existing(seen: set[str], combiner: Combiner) -> int:
    """Ingest any on-disk country pages not yet in jsonl (e.g. p1–p75+)."""
    total = 0
    for cc in COUNTRY_ORDER:
        pages = sorted(existing_pages(cc))
        if not pages:
            continue
        # chunk to keep memory bounded
        for i in range(0, len(pages), 80):
            chunk = pages[i : i + 80]
            written = normalize_pages(cc, chunk, seen)
            total += written
            if written:
                log(f"MERGE-EXISTING {cc} {chunk[0]}-{chunk[-1]} wrote={written}")
                combiner.note(written, f"existing-{cc}-{chunk[-1]}")
    return total


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    start = time.time()
    deadline = start + TIMEBOX_SEC
    log("START pull_himalayas_search IN→US,CA,GB,AU,IE timebox=12m sleep=150ms")

    seen = load_seen()
    log(f"jsonl existing unique urls={len(seen)}")
    combiner = Combiner()

    pre = merge_all_existing(seen, combiner)
    log(f"MERGE-EXISTING total wrote={pre} seen={len(seen)}")

    all_stats = []
    next_started = None
    for cc in COUNTRY_ORDER:
        if time.time() >= deadline and cc != "IN":
            log(f"SKIP {cc} timebox")
            all_stats.append({
                "cc": cc,
                "country": COUNTRY_NAME[cc],
                "complete": False,
                "stop_reason": "timebox-before-start",
                "pages_fetched": 0,
                "jobs_raw": 0,
                "disk_pages": len(existing_pages(cc)),
            })
            continue
        if next_started is None and cc != "IN":
            next_started = cc
        st = crawl_country(cc, seen, deadline, combiner)
        all_stats.append(st)
        log(
            f"DONE {cc} fetched={st['pages_fetched']} skipped={st['pages_skipped']} "
            f"raw={st['jobs_raw']} written={st['jobs_written']} complete={st['complete']} "
            f"reason={st['stop_reason']} disk={st.get('disk_pages')} max={st.get('disk_max')}"
        )
        if cc == "IN" and st.get("complete"):
            combiner.note(0, "after-india", force=True)
            # mark next country we will start
            next_started = "US"

    # final combine if leftover new rows or never combined
    if combiner.since_combine or combiner.combines == 0:
        combiner.note(0, "end", force=True)

    elapsed = time.time() - start
    in_st = next((s for s in all_stats if s.get("cc") == "IN"), {})
    started_after_in = None
    for s in all_stats:
        if s.get("cc") != "IN" and (s.get("pages_fetched") or 0) > 0:
            started_after_in = s["cc"]
            break
        if s.get("cc") != "IN" and s.get("stop_reason") not in ("timebox-before-start",):
            if s.get("pages_skipped") or s.get("pages_fetched"):
                started_after_in = s["cc"]
                break

    report = {
        "elapsed_sec": round(elapsed, 1),
        "in_complete": bool(in_st.get("complete")),
        "in_pages_disk": in_st.get("disk_pages"),
        "in_disk_max": in_st.get("disk_max"),
        "in_jobs_raw_this_run": in_st.get("jobs_raw"),
        "in_totalCount": in_st.get("totalCount"),
        "in_stop_reason": in_st.get("stop_reason"),
        "next_country_started": started_after_in,
        "jsonl_unique": len(seen),
        "jobs_added_this_run": combiner.total_added,
        "combines": combiner.combines,
        "countries": all_stats,
    }
    (RAW / "himalayas_search_pull_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log("REPORT " + json.dumps(report, ensure_ascii=False))
    log(f"FINISH elapsed={elapsed:.1f}s")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

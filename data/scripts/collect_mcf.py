#!/usr/bin/env python3
"""Collect MyCareersFuture public jobs JSON and normalize to JSONL."""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")
LOG = RAW / "mcf_log.txt"
OUT = NORM / "mycareersfuture.jsonl"

BASE = "https://api.mycareersfuture.gov.sg/v2/jobs"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
TIMEBOX_SEC = 12 * 60
SLEEP_SEC = 0.30
LIMIT = 100

REMOTE_RE = re.compile(
    r"remote|work[\s\-]*from[\s\-]*home|flexi[\s\-]*place|wfh|"
    r"telecommut|home[\s\-]*based|work[\s\-]*at[\s\-]*home|"
    r"hybrid[\s\-]*remote|\bfrom home\b",
    re.I,
)


class HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.parts)


def strip_html(text: object) -> str:
    if not text:
        return ""
    s = html.unescape(str(text))
    try:
        p = HTMLStripper()
        p.feed(s)
        s = p.get_text()
    except Exception:
        s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def short_desc(text: object, limit: int = 300) -> str:
    t = strip_html(text)
    return t if len(t) <= limit else t[:limit].rstrip()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def fetch(url: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status, resp.read(), ""
    except urllib.error.HTTPError as e:
        body = e.read() if e.fp else b""
        return e.code, body, str(e)
    except Exception as e:
        return 0, b"", f"{type(e).__name__}: {e}"


def fetch_retry(url: str) -> tuple[int, bytes, str, bool]:
    """Return status, body, err, retried."""
    status, body, err = fetch(url)
    retried = False
    if status == 429:
        log(f"429 on {url} — retry once after 3s")
        time.sleep(3)
        retried = True
        status, body, err = fetch(url)
    elif status == 0:
        log(f"network error on {url}: {err} — retry once after 3s")
        time.sleep(3)
        retried = True
        status, body, err = fetch(url)
    return status, body, err, retried


def first_url() -> str:
    return (
        f"{BASE}?limit={LIMIT}&sortBy=new_posting_date&order=desc&search="
    )


def collect() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    LOG.write_text("", encoding="utf-8")
    start = time.monotonic()
    url = first_url()
    page_n = 0
    jobs_raw = 0
    errors: list[str] = []
    advertised = None
    last_dates: list[str] = []

    log(f"start collect limit={LIMIT} timebox={TIMEBOX_SEC}s url={url}")

    while url:
        elapsed = time.monotonic() - start
        if elapsed >= TIMEBOX_SEC:
            log(f"timebox reached elapsed={elapsed:.1f}s after {page_n} pages")
            break

        status, body, err, retried = fetch_retry(url)
        page_n += 1
        dest = RAW / f"mcf_p{page_n}.json"

        if status != 200:
            msg = f"page {page_n} HTTP {status} err={err} url={url}"
            log(msg)
            errors.append(msg)
            dest.write_bytes(body or err.encode())
            break

        try:
            data = json.loads(body.decode("utf-8"))
        except Exception as e:
            msg = f"page {page_n} JSON parse error: {e}"
            log(msg)
            errors.append(msg)
            dest.write_bytes(body)
            break

        dest.write_bytes(body)
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            msg = f"page {page_n} missing results list keys={list(data)[:20] if isinstance(data, dict) else type(data)}"
            log(msg)
            errors.append(msg)
            break

        if advertised is None:
            advertised = data.get("total")
            log(f"advertised_total={advertised} countWithoutFilters={data.get('countWithoutFilters')}")

        n = len(results)
        jobs_raw += n
        dates = []
        for j in results:
            md = j.get("metadata") or {}
            if isinstance(md, dict) and md.get("newPostingDate"):
                dates.append(str(md["newPostingDate"]))
        date_span = ""
        if dates:
            date_span = f" dates={min(dates)}..{max(dates)}"
            last_dates = dates

        links = data.get("_links") or {}
        nxt = ""
        if isinstance(links, dict):
            nxt_obj = links.get("next") or {}
            if isinstance(nxt_obj, dict):
                nxt = nxt_obj.get("href") or ""

        log(
            f"page {page_n} status=200 n={n} saved={dest.name} "
            f"elapsed={time.monotonic()-start:.1f}s{date_span} next={bool(nxt)}"
        )

        if n == 0:
            log("empty page — stop")
            break
        if not nxt or nxt == url:
            log("no further next link — stop")
            break

        url = nxt
        time.sleep(SLEEP_SEC)

    summary = {
        "advertised_total": advertised,
        "pages_fetched": page_n,
        "jobs_raw": jobs_raw,
        "errors": errors,
        "elapsed_sec": round(time.monotonic() - start, 1),
        "last_dates": [min(last_dates), max(last_dates)] if last_dates else [],
    }
    log(f"collect done {json.dumps(summary, ensure_ascii=False)}")
    return summary


def company_name(job: dict) -> str:
    for key in ("postedCompany", "hiringCompany", "company"):
        obj = job.get(key)
        if isinstance(obj, dict) and obj.get("name"):
            return str(obj["name"]).strip()
        if isinstance(obj, str) and obj.strip():
            return obj.strip()
    return ""


def city_state(job: dict) -> tuple[str, str]:
    addr = job.get("address")
    if not isinstance(addr, dict):
        return "", ""
    city = ""
    state = ""
    districts = addr.get("districts") or []
    if isinstance(districts, list) and districts:
        d0 = districts[0]
        if isinstance(d0, dict):
            city = str(d0.get("location") or "").strip()
            state = str(d0.get("region") or d0.get("regionId") or "").strip()
    if not city:
        parts = []
        for k in ("building", "street", "block"):
            v = addr.get(k)
            if v:
                parts.append(str(v).strip())
        if addr.get("overseasCountry"):
            parts.append(str(addr["overseasCountry"]).strip())
        city = ", ".join(p for p in parts if p)
    return city, state


def is_remote(job: dict) -> bool:
    fwa = job.get("flexibleWorkArrangements")
    chunks: list[str] = []
    if isinstance(fwa, list):
        for item in fwa:
            if isinstance(item, dict):
                chunks.append(str(item.get("flexibleWorkArrangement") or ""))
                chunks.append(str(item.get("name") or ""))
                chunks.append(json.dumps(item, ensure_ascii=False))
            else:
                chunks.append(str(item))
    elif isinstance(fwa, dict):
        chunks.append(json.dumps(fwa, ensure_ascii=False))
    elif fwa:
        chunks.append(str(fwa))
    blob = " ".join(chunks)
    return bool(blob and REMOTE_RE.search(blob))


def job_url(job: dict) -> str:
    md = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    url = (md.get("jobDetailsUrl") or "").strip()
    if url:
        return url
    uid = job.get("uuid") or job.get("id") or ""
    if uid:
        return f"https://www.mycareersfuture.gov.sg/job/{uid}"
    return ""


def job_id(job: dict) -> str:
    uid = job.get("uuid") or job.get("id")
    if not uid:
        md = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        uid = md.get("jobPostId")
    if not uid:
        return ""
    return f"mcf:{uid}"


def posted_at(job: dict) -> str:
    md = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    return str(md.get("newPostingDate") or "")


def normalize_job(job: dict) -> dict | None:
    if not isinstance(job, dict):
        return None
    url = job_url(job)
    jid = job_id(job)
    title = str(job.get("title") or "").strip()
    if not url or not jid or not title:
        return None
    city, state = city_state(job)
    desc = job.get("description") or job.get("jobDescription") or ""
    return {
        "id": jid,
        "title": title,
        "company": company_name(job),
        "country": "Singapore",
        "state": state,
        "city": city,
        "remote": is_remote(job),
        "url": url,
        "posted_at": posted_at(job),
        "source": "mycareersfuture",
        "description": short_desc(desc, 300),
    }


def normalize() -> dict:
    NORM.mkdir(parents=True, exist_ok=True)
    pages = sorted(RAW.glob("mcf_p*.json"), key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))
    seen: set[str] = set()
    written = 0
    remote_n = 0
    skipped = 0
    dups = 0
    bad_pages = 0
    with OUT.open("w", encoding="utf-8") as fh:
        for path in pages:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                log(f"normalize skip {path.name}: {e}")
                bad_pages += 1
                continue
            results = data.get("results") if isinstance(data, dict) else None
            if not isinstance(results, list):
                bad_pages += 1
                continue
            for job in results:
                row = normalize_job(job)
                if not row:
                    skipped += 1
                    continue
                key = row["url"].strip().lower().rstrip("/")
                if key in seen:
                    dups += 1
                    continue
                seen.add(key)
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
                written += 1
                if row["remote"]:
                    remote_n += 1
    stats = {
        "pages": len(pages),
        "jobs_written": written,
        "remote": remote_n,
        "dups": dups,
        "skipped": skipped,
        "bad_pages": bad_pages,
        "out": str(OUT),
    }
    log(f"normalize done {json.dumps(stats, ensure_ascii=False)}")
    return stats


def main() -> int:
    col = collect()
    norm = normalize()
    print("COLLECT", json.dumps(col, ensure_ascii=False))
    print("NORMALIZE", json.dumps(norm, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

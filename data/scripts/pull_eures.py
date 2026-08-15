#!/usr/bin/env python3
"""Full-catalog EURES pull. Page size 50. No publicationPeriod."""
from __future__ import annotations

import html as htmlmod
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")
EURES_JSONL = NORM / "eures.jsonl"
COMBINED = Path("/workspace/jobs/remote-aug2026.jsonl")
THISMONTH = Path("/workspace/jobs/remote-aug2026-thismonth.jsonl")
SUMMARY = Path("/workspace/jobs/summary.json")
LOG = RAW / "eures_pull.log"
STATE = RAW / "eures_pull_state.json"
SEARCH_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
PAGE_SIZE = 50
MAX_PAGE = 200
SLEEP_MIN, SLEEP_MAX = 0.15, 0.30
FETCH_SECONDS = 11 * 60 + 30
TIMEOUT = 60
MONTH_CUTOFF = "2026-08-01"
FLUSH_EVERY = 10_000

COUNTRIES = [
    ("nl", "Netherlands"),
    ("fr", "France"),
    ("de", "Germany"),
    ("ie", "Ireland"),
]

# NUTS2/1 seeds so we can page past the 10k country window
NUTS = {
    "nl": [
        "nl11", "nl12", "nl13", "nl21", "nl22", "nl23",
        "nl32", "nl34", "nl35", "nl36", "nl41", "nl42", "nl-NS",
        "nl111", "nl112", "nl113", "nl124", "nl125", "nl126",
        "nl131", "nl132", "nl133", "nl211", "nl212", "nl213",
        "nl221", "nl224", "nl225", "nl226", "nl230",
        "nl310", "nl321", "nl323", "nl324", "nl325", "nl326",
        "nl327", "nl328", "nl329", "nl332", "nl333", "nl337",
        "nl341", "nl342", "nl411", "nl412", "nl413", "nl414",
        "nl421", "nl422", "nl423",
    ],
    "fr": [
        "fr10", "frb0", "frc1", "frc2", "frd1", "frd2",
        "fre1", "fre2", "frf1", "frf2", "frf3", "frg0",
        "frh0", "fri1", "fri2", "fri3", "frj1", "frj2",
        "frk1", "frk2", "frl0", "frm0",
        "fry1", "fry2", "fry3", "fry4", "fry5", "fr-NS",
    ],
    "de": [
        "de1", "de2", "de3", "de4", "de5", "de6", "de7",
        "de8", "de9", "dea", "deb", "dec", "ded", "dee",
        "def", "deg", "de-NS",
    ],
    "ie": [
        "ie041", "ie042", "ie051", "ie052", "ie053",
        "ie061", "ie062", "ie063", "ie-NS",
    ],
}

OFFERINGS = [
    "temporary", "directhire", "contract", "selfemployed",
    "internship", "apprenticeship", "voluntary", "seasonal", "NS",
]

REMOTE_RE = re.compile(
    r"(?i)(?<![\w-])(?:remote(?:ly)?|tele[\s-]?work(?:ing)?|thuiswerk(?:en)?|"
    r"home[\s-]?office|teletravail|télétravail|homeoffice)(?![\w-])"
)

start = time.time()
http_counts: dict[int, int] = {}
pages_by_cc: dict[str, int] = {cc: 0 for cc, _ in COUNTRIES}
last_page_by_cc: dict[str, str] = {}
jobs_by_cc: dict[str, int] = {cc: 0 for cc, _ in COUNTRIES}
errors: list[str] = []
new_unique_since_flush = 0
pending_combined: list[dict] = []
seen_eures_ids: set[str] = set()
seen_urls: set[str] = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def remaining() -> float:
    return FETCH_SECONDS - (time.time() - start)


def polite_sleep() -> None:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


def ms_to_iso(ms) -> str:
    if ms is None or ms == "":
        return ""
    try:
        val = float(ms)
        if val > 1e12:
            val /= 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return ""


def strip_html(text: str) -> str:
    if not text:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(text))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"[\r\t]+", " ", s)
    s = re.sub(r" *\n+ *", "\n", s)
    s = re.sub(r"[ ]{2,}", " ", s)
    return s.strip()


def http_json(body: dict) -> tuple[int, object | None, str]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    hdrs = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(SEARCH_URL, data=data, method="POST", headers=hdrs)

    def _do():
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw.decode("utf-8", errors="replace")), ""
            except json.JSONDecodeError as e:
                return r.status, None, f"json-decode: {e}"

    try:
        status, obj, err = _do()
        http_counts[status] = http_counts.get(status, 0) + 1
        return status, obj, err
    except urllib.error.HTTPError as e:
        raw = e.read()
        http_counts[e.code] = http_counts.get(e.code, 0) + 1
        snippet = raw[:400].decode("utf-8", errors="replace")
        if e.code == 429:
            log(f"429 wait-60s body={body}")
            time.sleep(60)
            try:
                status, obj, err = _do()
                http_counts[status] = http_counts.get(status, 0) + 1
                return status, obj, err
            except urllib.error.HTTPError as e2:
                raw2 = e2.read()
                http_counts[e2.code] = http_counts.get(e2.code, 0) + 1
                return e2.code, None, raw2[:400].decode("utf-8", errors="replace")
            except Exception as e2:
                return 0, None, str(e2)
        return e.code, None, snippet
    except Exception as e:
        log(f"net-error retry-once: {e}")
        time.sleep(2)
        try:
            status, obj, err = _do()
            http_counts[status] = http_counts.get(status, 0) + 1
            return status, obj, err
        except Exception as e2:
            return 0, None, str(e2)


def raw_path(cc: str, loc: str, offering: str, page: int) -> Path:
    if loc == cc and not offering:
        return RAW / f"eures_{cc}_p{page}.json"
    if offering:
        return RAW / f"eures_{cc}_{loc}_{offering}_p{page}.json"
    return RAW / f"eures_{cc}_{loc}_p{page}.json"


def next_country_page(cc: str) -> int:
    n = 1
    while (RAW / f"eures_{cc}_p{n}.json").exists():
        n += 1
    return n


def normalize_job(raw: dict, country_name: str) -> dict | None:
    jid = str(raw.get("id") or "").strip()
    if not jid:
        return None
    title = strip_html(str(raw.get("title") or "")).strip()
    desc_full = strip_html(str(raw.get("description") or ""))
    emp = raw.get("employer") if isinstance(raw.get("employer"), dict) else {}
    company = str((emp or {}).get("name") or "").strip()
    posted = ms_to_iso(raw.get("creationDate"))
    url = ""
    for key in ("url", "jobUrl", "jvUrl", "detailsUrl", "link"):
        val = raw.get(key)
        if isinstance(val, str) and val.startswith("http"):
            url = val
            break
    if not url:
        url = f"https://europa.eu/eures/portal/jv-se/jv-details/{urllib.parse.quote(jid, safe='')}"
    return {
        "id": f"eures:{jid}",
        "title": title,
        "company": company,
        "country": country_name,
        "state": "",
        "city": "",
        "remote": bool(REMOTE_RE.search(f"{title} {desc_full}")),
        "url": url,
        "posted_at": posted,
        "source": "eures",
        "description": desc_full[:300],
    }


def load_seen() -> None:
    if EURES_JSONL.exists():
        with EURES_JSONL.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("id"):
                    seen_eures_ids.add(row["id"])
                if row.get("url"):
                    seen_urls.add(row["url"])
    if COMBINED.exists():
        with COMBINED.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("url"):
                    seen_urls.add(row["url"])


def rewrite_summary() -> None:
    by_source: Counter[str] = Counter()
    by_country: Counter[str] = Counter()
    by_remote: Counter[str] = Counter()
    this_month = 0
    older_active = 0
    total = 0
    month_rows: list[dict] = []
    if COMBINED.exists():
        with COMBINED.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total += 1
                by_source[str(row.get("source") or "")] += 1
                by_country[str(row.get("country") or "")] += 1
                by_remote["remote" if row.get("remote") else "onsite"] += 1
                pa = str(row.get("posted_at") or "")
                if pa >= MONTH_CUTOFF:
                    this_month += 1
                    month_rows.append(row)
                else:
                    older_active += 1
    summary = {
        "total": total,
        "by_source": dict(by_source),
        "by_country": dict(by_country),
        "by_remote": dict(by_remote),
        "this_month": this_month,
        "older_active": older_active,
        "updated_at": now_iso(),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with THISMONTH.open("w", encoding="utf-8") as fh:
        for row in month_rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
    log(f"SUMMARY total={total} this_month={this_month} older_active={older_active} eures={by_source.get('eures', 0)}")


def flush_ingest(force: bool = False) -> None:
    global new_unique_since_flush, pending_combined
    if not pending_combined:
        return
    if not force and new_unique_since_flush < FLUSH_EVERY:
        return
    with COMBINED.open("a", encoding="utf-8") as fh:
        for row in pending_combined:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
    log(f"INGEST merged {len(pending_combined)} new unique (since_flush={new_unique_since_flush})")
    pending_combined = []
    new_unique_since_flush = 0
    rewrite_summary()


def accept_jobs(jvs: list, country_name: str) -> int:
    global new_unique_since_flush
    added = 0
    new_rows: list[dict] = []
    for raw in jvs:
        if not isinstance(raw, dict):
            continue
        job = normalize_job(raw, country_name)
        if not job:
            continue
        if job["id"] in seen_eures_ids:
            continue
        seen_eures_ids.add(job["id"])
        new_rows.append(job)
        if job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            pending_combined.append(job)
            new_unique_since_flush += 1
        added += 1
    if new_rows:
        with EURES_JSONL.open("a", encoding="utf-8") as fh:
            for job in new_rows:
                fh.write(json.dumps(job, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
    flush_ingest(False)
    return added


def ingest_existing_raw() -> None:
    files = sorted(RAW.glob("eures_*.json"))
    n = 0
    for path in files:
        if path.name.startswith("eures_nl_psize"):
            continue
        if path.name in {"eures_collect_summary.json", "eures_pull_state.json"}:
            continue
        if "_p" not in path.name:
            continue
        m = re.match(r"eures_([a-z]{2})", path.name)
        if not m:
            continue
        cc = m.group(1)
        country = dict(COUNTRIES).get(cc)
        if not country:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and "jvs" in payload:
            resp = payload
        elif isinstance(payload, dict) and isinstance(payload.get("response"), dict):
            resp = payload["response"]
        else:
            continue
        jvs = resp.get("jvs") or []
        if not isinstance(jvs, list):
            continue
        n += accept_jobs(jvs, country)
    log(f"INGEST existing raw added={n} eures_ids={len(seen_eures_ids)}")
    flush_ingest(True)


def save_state() -> None:
    STATE.write_text(json.dumps({
        "pages_by_cc": pages_by_cc,
        "last_page_by_cc": last_page_by_cc,
        "jobs_by_cc": jobs_by_cc,
        "http_counts": http_counts,
        "errors": errors[-20:],
        "elapsed_s": round(time.time() - start, 1),
    }, indent=2), encoding="utf-8")


def fetch_page(cc: str, loc: str, page: int, offering: str = "") -> tuple[int, list, int | None]:
    """Return (status, jvs, numberRecords). Writes raw file on 200."""
    path = raw_path(cc, loc, offering, page)
    if path.exists():
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            jvs = obj.get("jvs") if isinstance(obj, dict) else []
            total = obj.get("numberRecords") if isinstance(obj, dict) else None
            return 200, jvs if isinstance(jvs, list) else [], total if isinstance(total, int) else None
        except Exception:
            pass
    body: dict = {
        "locationCodes": [loc],
        "page": page,
        "resultsPerPage": PAGE_SIZE,
    }
    if offering:
        body["positionOfferingCodes"] = [offering]
    status, obj, err = http_json(body)
    if status != 200 or not isinstance(obj, dict):
        errors.append(f"{cc}/{loc}/{offering or '-'} p{page} status={status} err={(err or '')[:160]}")
        log(f"FAIL cc={cc} loc={loc} off={offering or '-'} p{page} status={status} err={(err or '')[:160]}")
        return status, [], None
    jvs = obj.get("jvs") if isinstance(obj.get("jvs"), list) else []
    total = obj.get("numberRecords") if isinstance(obj.get("numberRecords"), int) else None
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    pages_by_cc[cc] += 1
    jobs_by_cc[cc] += len(jvs)
    last_page_by_cc[cc] = path.name
    country = dict(COUNTRIES)[cc]
    added = accept_jobs(jvs, country)
    log(
        f"OK {path.name} n={total} got={len(jvs)} new={added} "
        f"pages={pages_by_cc[cc]} jobs={jobs_by_cc[cc]} "
        f"eures={len(seen_eures_ids)} left={remaining():.0f}s"
    )
    save_state()
    return status, jvs, total


def page_location(cc: str, loc: str, start_page: int, offering: str = "") -> None:
    page = start_page
    while page <= MAX_PAGE:
        if remaining() < 8:
            log(f"TIMEBOX stop cc={cc} loc={loc} p={page}")
            return
        path = raw_path(cc, loc, offering, page)
        existed = path.exists()
        status, jvs, total = fetch_page(cc, loc, page, offering)
        if status != 200:
            if status in (400, 500) and page > 1:
                return
            if status == 0:
                polite_sleep()
                page += 1
                continue
            return
        if not jvs:
            return
        if isinstance(total, int) and page * PAGE_SIZE >= total:
            return
        if len(jvs) < PAGE_SIZE:
            return
        page += 1
        if not existed:
            polite_sleep()


def collect_country(cc: str, name: str) -> None:
    if remaining() < 8:
        return
    start_p = next_country_page(cc)
    log(f"=== COUNTRY {cc} {name} start_page={start_p} ===")
    page_location(cc, cc, start_p)
    if remaining() < 8:
        return
    # shard to get past the 10k window
    for loc in NUTS.get(cc, []):
        if remaining() < 8:
            return
        shard_start = 1
        while raw_path(cc, loc, "", shard_start).exists():
            shard_start += 1
        # peek page 1 for size
        status, jvs, total = fetch_page(cc, loc, 1)
        if status != 200:
            continue
        if isinstance(total, int) and total > 10000:
            # page the 10k window then split by offering
            page_location(cc, loc, 2)
            for off in OFFERINGS:
                if remaining() < 8:
                    return
                off_start = 1
                while raw_path(cc, loc, off, off_start).exists():
                    off_start += 1
                page_location(cc, loc, off_start, off)
        else:
            page_location(cc, loc, 2)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    log(f"=== EURES full-catalog start PAGE_SIZE={PAGE_SIZE} no publicationPeriod ===")
    load_seen()
    log(f"seen eures_ids={len(seen_eures_ids)} urls={len(seen_urls)}")
    ingest_existing_raw()
    for cc, name in COUNTRIES:
        if remaining() < 8:
            log(f"TIMEBOX skip {cc}")
            break
        collect_country(cc, name)
    flush_ingest(True)
    save_state()
    log(f"DONE pages={pages_by_cc} last={last_page_by_cc} jobs={jobs_by_cc} http={http_counts}")
    print(json.dumps({
        "pages_by_cc": pages_by_cc,
        "last_page_by_cc": last_page_by_cc,
        "jobs_by_cc": jobs_by_cc,
        "eures_ids": len(seen_eures_ids),
        "http_counts": http_counts,
        "errors": errors[-10:],
        "elapsed_s": round(time.time() - start, 1),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

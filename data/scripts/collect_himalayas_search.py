#!/usr/bin/env python3
"""Page Himalayas /jobs/api/search by country (and city if supported)."""
from __future__ import annotations

import json
import os
import random
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")
LOG = RAW / "himalayas_country_log.txt"
JSONL = NORM / "himalayas.jsonl"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
BASE = "https://himalayas.app/jobs/api/search"
SLEEP_MIN = 0.12
SLEEP_MAX = 0.25
LIMIT = 20

COUNTRY_NAME = {
    "IN": "India",
    "NL": "Netherlands",
    "FR": "France",
    "SG": "Singapore",
    "AU": "Australia",
    "IE": "Ireland",
    "GB": "UK",
    "CA": "Canada",
    "DE": "Germany",
    "US": "USA",
}

# After IN: NL, FR, AU, SG, IE, GB, then CA, US last
COUNTRY_ORDER = ["IN", "NL", "FR", "AU", "SG", "IE", "GB", "CA", "DE"]  # US skipped: already well covered

CITY_QUERIES = {
    "NL": ["Rotterdam", "The Hague", "Utrecht", "Eindhoven"],
    "FR": [
        "Lyon", "Toulouse", "Lille", "Marseille", "Nantes",
        "Rennes", "Strasbourg", "Grenoble", "Nice", "Montpellier",
    ],
    "AU": ["Perth", "Western Australia"],
    "IE": ["Galway", "Limerick"],
    "GB": ["Cambridge", "Leeds", "Sheffield", "Bristol"],
}

CITY_STATE = {
    "rotterdam": "South Holland",
    "the hague": "South Holland",
    "den haag": "South Holland",
    "utrecht": "Utrecht",
    "eindhoven": "North Brabant",
    "amsterdam": "North Holland",
    "perth": "Western Australia",
    "sydney": "New South Wales",
    "melbourne": "Victoria",
    "brisbane": "Queensland",
    "adelaide": "South Australia",
    "canberra": "Australian Capital Territory",
    "lyon": "Auvergne-Rhône-Alpes",
    "toulouse": "Occitanie",
    "lille": "Hauts-de-France",
    "marseille": "Provence-Alpes-Côte d'Azur",
    "nantes": "Pays de la Loire",
    "rennes": "Brittany",
    "strasbourg": "Grand Est",
    "grenoble": "Auvergne-Rhône-Alpes",
    "nice": "Provence-Alpes-Côte d'Azur",
    "montpellier": "Occitanie",
    "paris": "Île-de-France",
    "cambridge": "East of England",
    "leeds": "Yorkshire and the Humber",
    "sheffield": "Yorkshire and the Humber",
    "bristol": "South West England",
    "london": "England",
    "manchester": "England",
    "galway": "County Galway",
    "limerick": "County Limerick",
    "dublin": "County Dublin",
    "cork": "County Cork",
    "singapore": "",
    "bengaluru": "Karnataka",
    "bangalore": "Karnataka",
    "hyderabad": "Telangana",
    "mumbai": "Maharashtra",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "pune": "Maharashtra",
    "chennai": "Tamil Nadu",
    "gurgaon": "Haryana",
    "gurugram": "Haryana",
    "noida": "Uttar Pradesh",
    "kolkata": "West Bengal",
    "ahmedabad": "Gujarat",
}

CITY_CANON = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "the hague": "The Hague",
    "den haag": "The Hague",
    "new delhi": "New Delhi",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
}


class _Strip(HTMLParser):
    def __init__(self):
        super().__init__()
        self.p = []

    def handle_data(self, d):
        self.p.append(d)


def strip_html(text):
    if not text:
        return ""
    s = str(text)
    st = _Strip()
    try:
        st.feed(s)
        st.close()
        s = "".join(st.p)
    except Exception:
        s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def polite_sleep():
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


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
    except URLError as e:
        return 0, str(e).encode()
    except Exception as e:
        return 0, str(e).encode()


def fetch_retry(url: str) -> tuple[int, bytes]:
    status, body = fetch(url)
    if status == 429:
        log(f"429 {url} wait 60s then retry")
        time.sleep(60)
        status, body = fetch(url)
        if status == 429:
            log(f"429-again {url}")
    return status, body


def existing_max_page(cc: str) -> int:
    rx = re.compile(rf"^himalayas_{cc.lower()}_p(\d+)\.json$")
    mx = 0
    for fn in os.listdir(RAW):
        m = rx.fullmatch(fn)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx


def search_url(cc: str, page: int, extra: dict | None = None) -> str:
    params = {"country": cc, "sort": "recent", "page": str(page)}
    if extra:
        params.update(extra)
    return f"{BASE}?{urlencode(params)}"


def save_page(cc: str, page: int, raw: bytes, suffix: str = "") -> Path:
    if suffix:
        path = RAW / f"himalayas_{cc.lower()}_{suffix}_p{page}.json"
    else:
        path = RAW / f"himalayas_{cc.lower()}_p{page}.json"
    if path.exists():
        return path
    tmp = path.with_suffix(".json.tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)
    return path


def page_country(cc: str, extra: dict | None = None, suffix: str = "", start_page: int = 1) -> dict:
    stats = {
        "cc": cc,
        "suffix": suffix,
        "totalCount": None,
        "pages": 0,
        "jobs": 0,
        "errors": [],
        "first_url": None,
    }
    page = start_page
    empty_streak = 0
    while True:
        if suffix:
            out = RAW / f"himalayas_{cc.lower()}_{suffix}_p{page}.json"
        else:
            out = RAW / f"himalayas_{cc.lower()}_p{page}.json"
        url = search_url(cc, page, extra)
        if stats["first_url"] is None:
            stats["first_url"] = url
        if out.exists() and out.stat().st_size > 20:
            try:
                d = json.loads(out.read_text(encoding="utf-8"))
                jobs = d.get("jobs") or []
                stats["totalCount"] = d.get("totalCount", stats["totalCount"])
                stats["pages"] += 1
                stats["jobs"] += len(jobs)
                if not jobs:
                    empty_streak += 1
                    if empty_streak >= 2:
                        break
                else:
                    empty_streak = 0
                tc = stats["totalCount"] or 0
                if page * LIMIT >= tc and tc > 0:
                    break
                page += 1
                continue
            except Exception:
                pass
        status, body = fetch_retry(url)
        if status != 200:
            stats["errors"].append(f"page={page} status={status} url={url}")
            log(f"ERR {cc} {suffix} page={page} status={status}")
            if status in (403, 429):
                break
            empty_streak += 1
            if empty_streak >= 3:
                break
            page += 1
            polite_sleep()
            continue
        try:
            d = json.loads(body)
        except Exception as e:
            stats["errors"].append(f"page={page} json {e}")
            log(f"ERR {cc} {suffix} page={page} bad json")
            break
        jobs = d.get("jobs") or []
        stats["totalCount"] = d.get("totalCount", stats["totalCount"])
        save_page(cc, page, body, suffix=suffix)
        stats["pages"] += 1
        stats["jobs"] += len(jobs)
        log(
            f"OK {cc} {suffix or 'country'} page={page} jobs={len(jobs)} "
            f"offset={d.get('offset')} totalCount={d.get('totalCount')} saved={out.name}"
        )
        if not jobs:
            empty_streak += 1
            if empty_streak >= 2:
                break
        else:
            empty_streak = 0
        tc = stats["totalCount"] or 0
        if page * LIMIT >= tc and tc > 0:
            break
        if len(jobs) < LIMIT:
            break
        page += 1
        polite_sleep()
    return stats


def probe_city_params(cc: str, city: str) -> tuple[str | None, int]:
    """Return (param_name, totalCount) for first working city filter."""
    candidates = [
        {"location": city},
        {"city": city},
        {"q": city},
        {"query": city},
    ]
    for extra in candidates:
        url = search_url(cc, 1, extra)
        status, body = fetch_retry(url)
        polite_sleep()
        if status != 200:
            log(f"PROBE city {cc} {city} {list(extra)} status={status}")
            continue
        try:
            d = json.loads(body)
        except Exception:
            continue
        tc = d.get("totalCount")
        jobs = d.get("jobs") or []
        key = next(iter(extra))
        log(f"PROBE city {cc} {city} param={key} totalCount={tc} njobs={len(jobs)}")
        # A useful city filter should shrink below the country total or mention the city
        if tc is None:
            continue
        return key, int(tc)
    return None, 0


# cache which city param works per country
_CITY_PARAM: dict[str, str | None] = {}


def page_cities(cc: str, country_total: int | None) -> list[dict]:
    cities = CITY_QUERIES.get(cc) or []
    out = []
    if not cities:
        return out
    # discover param once
    if cc not in _CITY_PARAM:
        param, tc = probe_city_params(cc, cities[0])
        _CITY_PARAM[cc] = param
        log(f"CITY-PARAM {cc}={param} first_city={cities[0]} tc={tc} country_tc={country_total}")
    param = _CITY_PARAM[cc]
    if not param:
        log(f"CITY-PARAM {cc} none — skip city pages")
        return out
    for city in cities:
        extra = {param: city}
        slug = re.sub(r"[^a-z0-9]+", "", city.lower())
        # skip if city filter returns same as full country (useless)
        url = search_url(cc, 1, extra)
        status, body = fetch_retry(url)
        polite_sleep()
        if status != 200:
            log(f"CITY skip {cc} {city} status={status}")
            continue
        try:
            d = json.loads(body)
        except Exception:
            continue
        tc = d.get("totalCount")
        log(f"CITY {cc} {city} param={param} totalCount={tc}")
        if country_total and tc and tc >= country_total:
            log(f"CITY {cc} {city} totalCount={tc} >= country {country_total} — filter ignored, skip paging")
            # still save page 1 for evidence
            save_page(cc, 1, body, suffix=slug)
            out.append({"cc": cc, "city": city, "totalCount": tc, "pages": 1, "skipped": True})
            continue
        st = page_country(cc, extra=extra, suffix=slug, start_page=1)
        st["city"] = city
        out.append(st)
    return out


def company_of(job: dict) -> str:
    name = (job.get("companyName") or "").strip()
    slug = (job.get("companySlug") or "").strip()
    if not name or name.lower() == "name":
        return slug
    return name


def url_of(job: dict) -> str:
    for k in ("guid", "applicationLink"):
        v = job.get(k)
        if v:
            return str(v).strip()
    slug = (job.get("companySlug") or "").strip()
    title = (job.get("title") or "").strip()
    if slug and title:
        tslug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return f"https://himalayas.app/companies/{slug}/jobs/{tslug}"
    return ""


def id_of(url: str, job: dict) -> str:
    if url:
        last = url.rstrip("/").split("/")[-1]
        if last:
            return f"himalayas:{last}"
    title = (job.get("title") or "job").strip()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"himalayas:{slug}"


def infer_city_state(job: dict, default_country: str) -> tuple[str, str]:
    blobs = []
    loc = job.get("locationRestrictions") or []
    if isinstance(loc, list):
        blobs.extend(str(x) for x in loc)
    elif loc:
        blobs.append(str(loc))
    for k in ("excerpt", "title", "description"):
        v = job.get(k)
        if v:
            blobs.append(strip_html(v)[:500])
    text = " ".join(blobs).lower()
    city = ""
    state = ""
    # prefer longer keys first
    keys = sorted(CITY_STATE.keys(), key=len, reverse=True)
    for key in keys:
        if re.search(rf"\b{re.escape(key)}\b", text):
            city = CITY_CANON.get(key, key.title())
            state = CITY_STATE[key]
            break
    return city, state


def normalize_job(job: dict, cc: str) -> dict | None:
    url = url_of(job)
    if not url:
        return None
    country = COUNTRY_NAME.get(cc, cc)
    city, state = infer_city_state(job, country)
    desc = job.get("excerpt") or ""
    if not desc:
        desc = strip_html(job.get("description") or "")[:300]
    else:
        desc = strip_html(desc)
    pub = job.get("pubDate")
    posted = pub if isinstance(pub, int) else (int(pub) if str(pub).isdigit() else pub)
    return {
        "id": id_of(url, job),
        "title": (job.get("title") or "").strip(),
        "company": company_of(job),
        "country": country,
        "state": state,
        "city": city,
        "remote": True,
        "url": url,
        "posted_at": posted if posted is not None else "",
        "source": "himalayas",
        "description": desc,
    }


def iter_new_raw_files() -> list[Path]:
    files = []
    rx = re.compile(r"^himalayas_([a-z]{2})(?:_[a-z0-9]+)?_p(\d+)\.json$")
    for fn in sorted(os.listdir(RAW)):
        if rx.fullmatch(fn):
            files.append(RAW / fn)
    return files


def merge_jsonl(files: list[Path] | None = None) -> dict:
    files = files if files is not None else iter_new_raw_files()
    seen: set[str] = set()
    existing_rows: list[str] = []
    if JSONL.exists():
        for line in JSONL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = (obj.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            existing_rows.append(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    added = 0
    skipped_no_url = 0
    new_rows: list[str] = []
    per_cc: dict[str, int] = {}
    for path in files:
        m = re.match(r"himalayas_([a-z]{2})", path.name)
        cc = m.group(1).upper() if m else ""
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"MERGE skip {path.name}: {e}")
            continue
        jobs = d.get("jobs") if isinstance(d, dict) else None
        if not isinstance(jobs, list):
            continue
        for job in jobs:
            row = normalize_job(job, cc)
            if not row:
                skipped_no_url += 1
                continue
            if row["url"] in seen:
                continue
            seen.add(row["url"])
            new_rows.append(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            added += 1
            per_cc[cc] = per_cc.get(cc, 0) + 1
    if new_rows:
        with JSONL.open("a", encoding="utf-8") as fh:
            for r in new_rows:
                fh.write(r + "\n")
    summary = {
        "existing": len(existing_rows),
        "added": added,
        "total": len(existing_rows) + added,
        "skipped_no_url": skipped_no_url,
        "added_by_cc": per_cc,
        "files": len(files),
    }
    log(f"MERGE {json.dumps(summary)}")
    return summary


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    log("START himalayas country search collector")
    log("PROBE note: /jobs/api?country= ignores filter (100k catalog). Using /jobs/api/search")

    all_stats = []
    # India first — must complete
    for cc in COUNTRY_ORDER:
        log(f"==== COUNTRY {cc} {COUNTRY_NAME.get(cc)} ====")
        st = page_country(cc)
        all_stats.append(st)
        log(f"DONE {cc} totalCount={st['totalCount']} pages={st['pages']} jobs={st['jobs']} errors={st['errors']}")
        # city probes for gap countries
        if cc in CITY_QUERIES:
            city_stats = page_cities(cc, st.get("totalCount"))
            all_stats.extend(city_stats)
        if cc == "IN":
            merge_jsonl()
            log("RUN combine.py after India")
            os.system("python3 /workspace/jobs/scripts/combine.py")
        # DE is last / optional

    merge_jsonl()
    log("RUN combine.py at end")
    os.system("python3 /workspace/jobs/scripts/combine.py")
    log("FINISH collector")
    # write a compact summary at end of log
    log("SUMMARY " + json.dumps([
        {k: s.get(k) for k in ("cc", "suffix", "city", "totalCount", "pages", "jobs", "errors", "skipped")}
        for s in all_stats
    ], ensure_ascii=False))


if __name__ == "__main__":
    main()

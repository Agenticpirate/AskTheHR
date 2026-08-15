#!/usr/bin/env python3
"""Collect LAST_WEEK EURES jobs for NL/FR/IE/DE. Public API, no key."""
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
from datetime import datetime, timezone
from pathlib import Path

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")
LOG = RAW / "eures_log.txt"
OUT = NORM / "eures.jsonl"
SEARCH_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
STATS_URL = "https://europa.eu/eures/api/jv-searchengine/public/statistics/getNumberOfJobs"
COUNTRY_STATS_URL = "https://europa.eu/eures/api/jv-searchengine/public/statistics/getCountryStats"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
PAGE_SIZE = 50
MAX_PAGE = 200  # API rejects page 201 at 50/page ("Too many results were requested")
SLEEP_MIN, SLEEP_MAX = 0.20, 0.40
FETCH_SECONDS = 11 * 60  # leave ~1 min for normalize + combine
TIMEOUT = 90

COUNTRIES = [
    ("ie", "Ireland", "Ireland"),
    ("nl", "Netherlands", "Netherlands"),
    ("fr", "France", "France"),
    ("de", "Germany", "Germany"),
]

# NUTS codes seen in locationMap / country-stats children → state (never invent cities)
NUTS_STATE = {
    "ie041": "Border", "ie042": "West", "ie051": "Mid-West", "ie052": "South-East",
    "ie053": "South-West", "ie061": "Dublin", "ie062": "Mid-East", "ie063": "Midland",
    "nl11": "Groningen", "nl12": "Friesland", "nl13": "Drenthe", "nl21": "Overijssel",
    "nl22": "Gelderland", "nl23": "Flevoland", "nl32": "Noord-Holland", "nl33": "Zuid-Holland",
    "nl34": "Zeeland", "nl35": "Utrecht", "nl36": "Zuid-Holland", "nl41": "Noord-Brabant",
    "nl42": "Limburg",
    "de1": "Baden-Württemberg", "de2": "Bayern", "de3": "Berlin", "de4": "Brandenburg",
    "de5": "Bremen", "de6": "Hamburg", "de7": "Hessen", "de8": "Mecklenburg-Vorpommern",
    "de9": "Niedersachsen", "dea": "Nordrhein-Westfalen", "deb": "Rheinland-Pfalz",
    "dec": "Saarland", "ded": "Sachsen", "dee": "Sachsen-Anhalt",
    "def": "Schleswig-Holstein", "deg": "Thüringen",
    "fr10": "Île-de-France", "frb0": "Centre-Val de Loire", "frc1": "Bourgogne",
    "frc2": "Franche-Comté", "frd1": "Basse-Normandie", "frd2": "Haute-Normandie",
    "fre1": "Nord-Pas-de-Calais", "fre2": "Picardie", "frf1": "Alsace",
    "frf2": "Champagne-Ardenne", "frf3": "Lorraine", "frg0": "Pays de la Loire",
    "frh0": "Bretagne", "fri1": "Aquitaine", "fri2": "Limousin", "fri3": "Poitou-Charentes",
    "frj1": "Languedoc-Roussillon", "frj2": "Midi-Pyrénées", "frk1": "Auvergne",
    "frk2": "Rhône-Alpes", "frl0": "Provence-Alpes-Côte d'Azur", "frm0": "Corse",
    "fry1": "Guadeloupe", "fry2": "Martinique", "fry3": "Guyane", "fry4": "La Réunion",
    "fry5": "Mayotte",
}

REMOTE_RE = re.compile(
    r"(?i)(?<![\w-])(?:remote(?:ly)?|home[\s-]?office|homeoffice|tele[\s-]?work(?:ing)?|hybrid[\s-]?remote)(?![\w-])"
)

start = time.time()
errors: list[str] = []
pages_fetched = 0
http_counts: dict[int, int] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def remaining() -> float:
    return FETCH_SECONDS - (time.time() - start)


def polite_sleep() -> None:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


def http_json(url: str, body: dict | None = None, method: str | None = None) -> tuple[int, object | None, str]:
    """Return (status, parsed_json_or_None, err_text). Retry once on 429 after 3s; once on timeout."""
    data = None
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
        method = method or "POST"
    req = urllib.request.Request(url, data=data, method=method or "GET", headers=hdrs)

    def _do():
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            status = r.status
            try:
                return status, json.loads(raw.decode("utf-8", errors="replace")), ""
            except json.JSONDecodeError as e:
                return status, None, f"json-decode: {e}"

    try:
        status, obj, err = _do()
        http_counts[status] = http_counts.get(status, 0) + 1
        return status, obj, err
    except urllib.error.HTTPError as e:
        raw = e.read()
        http_counts[e.code] = http_counts.get(e.code, 0) + 1
        if e.code == 429:
            log(f"429 retry-after-3s url={url} body={body}")
            time.sleep(3)
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
        return e.code, None, raw[:400].decode("utf-8", errors="replace")
    except Exception as e:
        log(f"net-error retry-once: {e} body={body}")
        time.sleep(2)
        try:
            status, obj, err = _do()
            http_counts[status] = http_counts.get(status, 0) + 1
            return status, obj, err
        except Exception as e2:
            return 0, None, str(e2)


def strip_html(text: str) -> str:
    if not text:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", text)
    s = re.sub(r"(?i)</p>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"[\r\t]+", " ", s)
    s = re.sub(r" *\n+ *", "\n", s)
    s = re.sub(r"[ ]{2,}", " ", s)
    return s.strip()


def ms_to_iso(ms) -> str:
    if ms is None or ms == "":
        return ""
    try:
        val = float(ms)
        if val > 1e12:
            val = val / 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return ""


def loc_state_city(location_map, country_name: str) -> tuple[str, str]:
    if not isinstance(location_map, dict):
        return "", ""
    # Prefer the queried country's codes
    values = []
    for key, vals in location_map.items():
        if isinstance(vals, list):
            values.extend(vals)
        elif vals:
            values.append(vals)
    codes = [str(v).strip() for v in values if v]
    state = ""
    city = ""
    for code in codes:
        mapped = NUTS_STATE.get(code.lower())
        if mapped:
            # Dublin is a city; other NUTS2/3 treated as state
            if code.lower() == "ie061":
                city = "Dublin"
                state = "Dublin"
            elif not state:
                state = mapped
        elif not city and not re.fullmatch(r"[a-z]{2}\w*", code.lower()):
            city = code  # human-readable place name if API ever sends one
    return state, city


def is_remote(title: str, description: str, extra: str) -> bool:
    blob = " ".join(x for x in (title, description, extra) if x)
    return bool(REMOTE_RE.search(blob))


def job_url(jid: str) -> str:
    enc = urllib.parse.quote(jid, safe="")
    return f"https://europa.eu/eures/portal/jv-se/jv-details/{enc}"


def normalize_job(raw: dict, country_name: str) -> dict | None:
    jid = str(raw.get("id") or "").strip()
    if not jid:
        return None
    title = strip_html(str(raw.get("title") or "")).strip()
    desc_full = strip_html(str(raw.get("description") or ""))
    desc = desc_full[:300]
    emp = raw.get("employer") if isinstance(raw.get("employer"), dict) else {}
    company = str((emp or {}).get("name") or "").strip()
    posted = ms_to_iso(raw.get("creationDate")) or ms_to_iso(raw.get("lastModificationDate"))
    extra_bits = []
    for key in ("positionScheduleCodes", "positionOfferingCode", "euresFlag"):
        val = raw.get(key)
        if val is not None:
            extra_bits.append(json.dumps(val, ensure_ascii=False))
    state, city = loc_state_city(raw.get("locationMap"), country_name)
    return {
        "id": f"eures:{jid}",
        "title": title,
        "company": company,
        "country": country_name,
        "state": state,
        "city": city,
        "remote": is_remote(title, desc_full, " ".join(extra_bits)),
        "url": job_url(jid),
        "posted_at": posted,
        "source": "eures",
        "description": desc,
    }


def save_raw(cc: str, page_n: int, query: dict, status: int, obj) -> Path:
    path = RAW / f"eures_{cc}_p{page_n}.json"
    payload = {
        "query": query,
        "http_status": status,
        "fetched_at": now_iso(),
        "response": obj,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def collect_query(cc: str, country_name: str, location_code: str, page_counter: list[int]) -> tuple[int, int]:
    """Fetch up to MAX_PAGE pages for one locationCodes value. Returns (pages, jobs_in_pages)."""
    global pages_fetched
    jobs_in = 0
    total = None
    page = 1
    while page <= MAX_PAGE:
        if remaining() < 2.5:
            log(f"TIMEBOX stop mid-query cc={cc} loc={location_code} page={page}")
            break
        query = {
            "locationCodes": [location_code],
            "publicationPeriod": "LAST_WEEK",
            "page": page,
            "resultsPerPage": PAGE_SIZE,
        }
        status, obj, err = http_json(SEARCH_URL, body=query)
        page_counter[0] += 1
        n = page_counter[0]
        save_raw(cc, n, query, status, obj if obj is not None else {"error": err})
        pages_fetched += 1
        if status != 200 or not isinstance(obj, dict):
            msg = f"FAIL cc={cc} loc={location_code} page={page} file=p{n} status={status} err={err[:180]}"
            log(msg)
            errors.append(msg)
            # page cap or bad page — stop this query
            break
        jvs = obj.get("jvs") if isinstance(obj.get("jvs"), list) else []
        total = obj.get("numberRecords")
        jobs_in += len(jvs)
        log(f"OK cc={cc} loc={location_code} page={page}/{MAX_PAGE} file=p{n} n={total} got={len(jvs)} elapsed={time.time()-start:.1f}s left={remaining():.0f}s")
        if page == 1 and isinstance(total, int):
            needed = min(MAX_PAGE, (total + PAGE_SIZE - 1) // PAGE_SIZE if total else 0)
            log(f"PLAN cc={cc} loc={location_code} last_week={total} pages_needed={needed}")
        if not jvs:
            break
        if isinstance(total, int) and page * PAGE_SIZE >= total:
            break
        if len(jvs) < PAGE_SIZE:
            break
        page += 1
        polite_sleep()
    return page - 1 if page > 1 else (1 if jobs_in else 0), jobs_in


def load_country_children() -> dict[str, list[tuple[str, int]]]:
    status, obj, err = http_json(COUNTRY_STATS_URL)
    if status != 200 or not isinstance(obj, list):
        log(f"country-stats fail status={status} err={err}")
        return {}
    (RAW / "eures_country_stats.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    out: dict[str, list[tuple[str, int]]] = {}
    for row in obj:
        code = (row.get("code") or "").lower()
        kids = []
        for c in row.get("children") or []:
            kc = (c.get("code") or "").strip()
            if not kc or kc.upper() == "NS":
                continue
            kids.append((kc, int(c.get("jobs") or 0)))
        kids.sort(key=lambda x: x[1])  # smallest first for leftover region splits
        out[code] = kids
        if code in {"de", "fr", "nl", "ie"}:
            log(f"STAT {row.get('label')} ({code}) jobs={row.get('jobs')} children={len(kids)}")
    return out


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    log("=== EURES collect start ===")
    log(f"body_that_works={{locationCodes:[cc], publicationPeriod:LAST_WEEK, page:1..200, resultsPerPage:50}}")
    log("unknown fields (keywords, lang, pageSize, offset) → 400 invalid-json; page=0 → 500; page 201@50 → too many results")

    status, obj, err = http_json(STATS_URL)
    if status == 200 and isinstance(obj, dict):
        log(f"live_total numberOfJobs={obj.get('numberOfJobs')}")
        (RAW / "eures_number_of_jobs.json").write_text(json.dumps(obj), encoding="utf-8")
    else:
        log(f"numberOfJobs fail status={status} err={err}")

    children = load_country_children()
    polite_sleep()

    # LAST_WEEK totals probe (page 1, size 5) per country
    last_week = {}
    for cc, country_name, _ in COUNTRIES:
        if remaining() < 3:
            break
        q = {"locationCodes": [cc], "publicationPeriod": "LAST_WEEK", "page": 1, "resultsPerPage": 5}
        status, obj, err = http_json(SEARCH_URL, body=q)
        nrec = obj.get("numberRecords") if isinstance(obj, dict) else None
        last_week[cc] = nrec
        log(f"PROBE LAST_WEEK {cc} ({country_name}) numberRecords={nrec} status={status}")
        polite_sleep()

    page_counter = {cc: [0] for cc, _, _ in COUNTRIES}
    fetched_jobs_raw = {cc: 0 for cc, _, _ in COUNTRIES}
    pages_by_cc = {cc: 0 for cc, _, _ in COUNTRIES}

    # 1) country-level each, IE first (completable), then NL/FR/DE up to 10k cap
    for cc, country_name, _ in COUNTRIES:
        if remaining() < 3:
            log(f"TIMEBOX skip country-level {cc}")
            break
        log(f"=== COUNTRY {cc} {country_name} LAST_WEEK={last_week.get(cc)} ===")
        pages, njob = collect_query(cc, country_name, cc, page_counter[cc])
        pages_by_cc[cc] += pages
        fetched_jobs_raw[cc] += njob
        log(f"DONE country-level {cc} pages={pages} raw_jobs={njob} left={remaining():.0f}s")

    # 2) If time remains after a 10k cap, split large remaining countries by smaller NUTS
    #    Only for countries that hit the cap and still have budget.
    for cc, country_name, _ in COUNTRIES:
        if remaining() < 8:
            break
        nrec = last_week.get(cc) or 0
        if not isinstance(nrec, int) or nrec <= PAGE_SIZE * MAX_PAGE:
            continue  # already complete at country level
        kids = children.get(cc) or []
        # Prefer larger slices that still fit under 10k LAST_WEEK-ish: use all-time as proxy,
        # fetch biggest-under-cap last; actually fetch largest remaining regions to add unique volume.
        # Sort largest first so each query adds up to 10k new-ish jobs.
        kids_large_first = sorted(kids, key=lambda x: -x[1])
        log(f"=== REGION SPLIT {cc} kids={len(kids_large_first)} left={remaining():.0f}s ===")
        for code, all_jobs in kids_large_first:
            if remaining() < 8:
                log(f"TIMEBOX stop regions cc={cc}")
                break
            pages, njob = collect_query(cc, country_name, code, page_counter[cc])
            pages_by_cc[cc] += pages
            fetched_jobs_raw[cc] += njob

    log(f"FETCH END pages_fetched={pages_fetched} by_cc={pages_by_cc} raw_jobs={fetched_jobs_raw} errors={len(errors)} elapsed={time.time()-start:.1f}s")

    # Normalize from all raw eures_{cc}_pN.json
    cc_to_country = {cc: name for cc, name, _ in COUNTRIES}
    seen_urls: set[str] = set()
    written = 0
    remote_n = 0
    onsite_n = 0
    by_cc_written = {cc: 0 for cc in cc_to_country}
    skipped_no_id = 0
    dups = 0

    files = sorted(RAW.glob("eures_*_p*.json"), key=lambda p: p.name)
    rows: list[dict] = []
    for path in files:
        # eures_nl_p12.json
        m = re.match(r"eures_([a-z]{2})_p\d+\.json$", path.name)
        if not m:
            continue
        cc = m.group(1)
        country_name = cc_to_country.get(cc)
        if not country_name:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"read {path.name}: {e}")
            continue
        resp = payload.get("response") if isinstance(payload, dict) else None
        jvs = []
        if isinstance(resp, dict):
            jvs = resp.get("jvs") or []
        if not isinstance(jvs, list):
            continue
        for rawj in jvs:
            if not isinstance(rawj, dict):
                continue
            job = normalize_job(rawj, country_name)
            if not job:
                skipped_no_id += 1
                continue
            url = job["url"]
            if url in seen_urls:
                dups += 1
                continue
            seen_urls.add(url)
            rows.append(job)
            written += 1
            by_cc_written[cc] += 1
            if job["remote"]:
                remote_n += 1
            else:
                onsite_n += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for job in rows:
            fh.write(json.dumps(job, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")

    summary = {
        "written": written,
        "remote": remote_n,
        "onsite": onsite_n,
        "dups_dropped": dups,
        "skipped_no_id": skipped_no_id,
        "by_country_written": by_cc_written,
        "pages_fetched": pages_fetched,
        "pages_by_cc": pages_by_cc,
        "raw_jobs_seen": fetched_jobs_raw,
        "last_week_totals": last_week,
        "errors": errors,
        "http_counts": http_counts,
        "out": str(OUT),
        "elapsed_s": round(time.time() - start, 1),
    }
    (RAW / "eures_collect_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"NORMALIZE written={written} remote={remote_n} onsite={onsite_n} dups={dups} path={OUT}")
    log("=== EURES collect done ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

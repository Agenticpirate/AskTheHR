#!/usr/bin/env python3
"""Incremental EURES collector. Writes JSONL as pages arrive. No short timebox."""
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

ROOT = Path("/workspace/jobs")
RAW = ROOT / "raw"
NORM = ROOT / "normalized"
DEBUG = ROOT / "debug"
OUT = NORM / "eures.jsonl"
SEEN_PATH = RAW / "eures_seen_urls.txt"
LOG = RAW / "eures_inc_log.txt"
SEARCH_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
STATS_URL = "https://europa.eu/eures/api/jv-searchengine/public/statistics/getNumberOfJobs"
COUNTRY_STATS_URL = "https://europa.eu/eures/api/jv-searchengine/public/statistics/getCountryStats"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0; +https://europa.eu/eures)"
PAGE_SIZE = 50
MAX_PAGE = 200
SLEEP_MIN, SLEEP_MAX = 0.18, 0.35
TIMEOUT = 90

COUNTRIES = [
    ("ie", "Ireland"),
    ("nl", "Netherlands"),
    ("fr", "France"),
    ("de", "Germany"),
]

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
    r"(?i)(?<![\w-])(?:remote(?:ly)?|home[\s-]?office|homeoffice|tele[\s-]?work(?:ing)?|hybrid[\s-]?remote|télétravail|telewerk)(?![\w-])"
)

http_counts: dict[int, int] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def polite_sleep(mult: float = 1.0) -> None:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX) * mult)


def http_json(url: str, body: dict | None = None, method: str | None = None) -> tuple[int, object | None, str]:
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

    for attempt in range(1, 8):
        try:
            status, obj, err = _do()
            http_counts[status] = http_counts.get(status, 0) + 1
            return status, obj, err
        except urllib.error.HTTPError as e:
            raw = e.read()
            http_counts[e.code] = http_counts.get(e.code, 0) + 1
            if e.code == 429:
                wait = min(3 * (2 ** (attempt - 1)), 90)
                log(f"429 backoff {wait}s attempt={attempt} body={body}")
                time.sleep(wait)
                continue
            if 500 <= e.code < 600:
                wait = min(2 ** attempt, 40)
                log(f"{e.code} backoff {wait}s attempt={attempt}")
                time.sleep(wait)
                continue
            return e.code, None, raw[:400].decode("utf-8", errors="replace")
        except Exception as e:
            wait = min(2 ** attempt, 30)
            log(f"net-error {e} wait={wait}s attempt={attempt}")
            time.sleep(wait)
    return 0, None, "retries-exhausted"


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


def loc_state_city(location_map) -> tuple[str, str]:
    if not isinstance(location_map, dict):
        return "", ""
    values = []
    for _key, vals in location_map.items():
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
            if code.lower() == "ie061":
                city = "Dublin"
                state = "Dublin"
            elif not state:
                state = mapped
        elif not city and not re.fullmatch(r"[a-z]{2}\w*", code.lower()):
            city = code
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
    state, city = loc_state_city(raw.get("locationMap"))
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


def load_seen() -> set[str]:
    seen: set[str] = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj.get("url"):
                    seen.add(obj["url"])
    if SEEN_PATH.exists():
        for line in SEEN_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                seen.add(line.strip())
    return seen


def append_jobs(jobs: list[dict], seen: set[str]) -> int:
    if not jobs:
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with OUT.open("a", encoding="utf-8") as fh, SEEN_PATH.open("a", encoding="utf-8") as sh:
        for job in jobs:
            url = job.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            fh.write(json.dumps(job, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
            sh.write(url + "\n")
            n += 1
        fh.flush()
        sh.flush()
    return n


def ingest_existing_raw(seen: set[str], cc_to_country: dict[str, str]) -> int:
    added = 0
    for path in sorted(RAW.glob("eures*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        resp = payload
        if isinstance(payload, dict) and "response" in payload and isinstance(payload["response"], dict):
            resp = payload["response"]
        if not isinstance(resp, dict):
            continue
        jvs = resp.get("jvs") or []
        if not isinstance(jvs, list):
            continue
        cc = ""
        m = re.search(r"eures_([a-z]{2})", path.name)
        if m:
            cc = m.group(1)
        country = cc_to_country.get(cc, "Netherlands" if "nl" in path.name else "")
        if not country:
            # infer from first job locationMap
            if jvs and isinstance(jvs[0], dict):
                lm = jvs[0].get("locationMap") or {}
                if isinstance(lm, dict) and lm:
                    k = next(iter(lm.keys())).lower()
                    country = dict(COUNTRIES).get(k, "")
        if not country:
            country = "Unknown"
        rows = []
        for rawj in jvs:
            if isinstance(rawj, dict):
                job = normalize_job(rawj, country)
                if job:
                    rows.append(job)
        added += append_jobs(rows, seen)
    return added


def collect_query(cc: str, country_name: str, location_code: str, seen: set[str], period: str = "LAST_WEEK") -> tuple[int, int, int]:
    """Returns (pages, raw_jobs, written)."""
    pages = 0
    raw_n = 0
    written = 0
    page = 1
    while page <= MAX_PAGE:
        query = {
            "locationCodes": [location_code],
            "publicationPeriod": period,
            "page": page,
            "resultsPerPage": PAGE_SIZE,
        }
        status, obj, err = http_json(SEARCH_URL, body=query)
        pages += 1
        if status != 200 or not isinstance(obj, dict):
            log(f"FAIL cc={cc} loc={location_code} page={page} status={status} err={str(err)[:180]}")
            break
        jvs = obj.get("jvs") if isinstance(obj.get("jvs"), list) else []
        total = obj.get("numberRecords")
        raw_n += len(jvs)
        rows = []
        for rawj in jvs:
            if isinstance(rawj, dict):
                job = normalize_job(rawj, country_name)
                if job:
                    rows.append(job)
        w = append_jobs(rows, seen)
        written += w
        if page == 1 or page % 10 == 0 or not jvs:
            log(
                f"OK cc={cc} loc={location_code} period={period} page={page} "
                f"n={total} got={len(jvs)} wrote={w} file_total={len(seen)}"
            )
        if not jvs:
            break
        if isinstance(total, int) and page * PAGE_SIZE >= total:
            break
        if len(jvs) < PAGE_SIZE:
            break
        page += 1
        polite_sleep()
    return pages, raw_n, written


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
            # grandchildren if present
            for g in c.get("children") or []:
                gc = (g.get("code") or "").strip()
                if gc and gc.upper() != "NS":
                    kids.append((gc, int(g.get("jobs") or 0)))
        kids.sort(key=lambda x: -x[1])
        out[code] = kids
        if code in {"de", "fr", "nl", "ie"}:
            log(f"STAT {row.get('label')} ({code}) jobs={row.get('jobs')} children={len(kids)}")
    return out


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    log("=== EURES incremental collect start ===")
    seen = load_seen()
    log(f"resume seen={len(seen)} out={OUT}")
    cc_to_country = {cc: name for cc, name in COUNTRIES}
    ingested = ingest_existing_raw(seen, cc_to_country)
    log(f"ingested existing raw wrote={ingested} seen={len(seen)}")

    status, obj, err = http_json(STATS_URL)
    if status == 200 and isinstance(obj, dict):
        log(f"live_total numberOfJobs={obj.get('numberOfJobs')}")
    children = load_country_children()
    polite_sleep()

    last_week = {}
    for cc, country_name in COUNTRIES:
        q = {"locationCodes": [cc], "publicationPeriod": "LAST_WEEK", "page": 1, "resultsPerPage": 5}
        status, obj, err = http_json(SEARCH_URL, body=q)
        nrec = obj.get("numberRecords") if isinstance(obj, dict) else None
        last_week[cc] = nrec
        log(f"PROBE LAST_WEEK {cc} ({country_name}) numberRecords={nrec} status={status}")
        polite_sleep()

    # IE first (completable), then others: country-level up to 10k, then NUTS splits
    for cc, country_name in COUNTRIES:
        nrec = last_week.get(cc) or 0
        log(f"=== COUNTRY {cc} {country_name} LAST_WEEK={nrec} ===")
        pages, raw_n, written = collect_query(cc, country_name, cc, seen, "LAST_WEEK")
        log(f"DONE country-level {cc} pages={pages} raw={raw_n} wrote={written} seen={len(seen)}")
        cap = PAGE_SIZE * MAX_PAGE
        if isinstance(nrec, int) and nrec > cap:
            kids = children.get(cc) or []
            log(f"=== REGION SPLIT {cc} kids={len(kids)} ===")
            for code, all_jobs in kids:
                pages, raw_n, written = collect_query(cc, country_name, code, seen, "LAST_WEEK")
                log(f"DONE region {cc}/{code} alltime~{all_jobs} pages={pages} raw={raw_n} wrote={written} seen={len(seen)}")
                polite_sleep()

    log(f"=== EURES collect done seen={len(seen)} http={http_counts} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

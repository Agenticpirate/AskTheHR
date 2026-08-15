#!/usr/bin/env python3
"""Fast EURES LAST_WEEK collector: nl, fr, ie, de. Writes raw pages immediately."""
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
DEBUG = Path("/workspace/jobs/debug")
OUT = NORM / "eures.jsonl"
SEARCH_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
PAGE_SIZE = 50
MAX_PAGE = 200
SLEEP_MIN, SLEEP_MAX = 0.20, 0.40
FETCH_SECONDS = 10 * 60  # leave time for normalize + combine
TIMEOUT = 45

COUNTRIES = [
    ("nl", "Netherlands"),
    ("fr", "France"),
    ("ie", "Ireland"),
    ("de", "Germany"),
]

# NUTS2/3 prefixes → state. Longer keys first when matching.
NUTS_STATE = {
    # Ireland NUTS3
    "ie041": "Border", "ie042": "West", "ie051": "Mid-West", "ie052": "South-East",
    "ie053": "South-West", "ie061": "Dublin", "ie062": "Mid-East", "ie063": "Midland",
    "ie04": "Northern and Western", "ie05": "Southern", "ie06": "Eastern and Midland",
    # Netherlands NUTS2
    "nl11": "Groningen", "nl12": "Friesland", "nl13": "Drenthe",
    "nl21": "Overijssel", "nl22": "Gelderland", "nl23": "Flevoland",
    "nl31": "Utrecht", "nl32": "Noord-Holland", "nl33": "Zuid-Holland", "nl34": "Zeeland",
    "nl35": "Utrecht", "nl36": "Zuid-Holland",
    "nl41": "Noord-Brabant", "nl42": "Limburg",
    "nl1": "Noord-Nederland", "nl2": "Oost-Nederland", "nl3": "West-Nederland", "nl4": "Zuid-Nederland",
    # Germany NUTS1
    "de1": "Baden-Württemberg", "de2": "Bayern", "de3": "Berlin", "de4": "Brandenburg",
    "de5": "Bremen", "de6": "Hamburg", "de7": "Hessen", "de8": "Mecklenburg-Vorpommern",
    "de9": "Niedersachsen", "dea": "Nordrhein-Westfalen", "deb": "Rheinland-Pfalz",
    "dec": "Saarland", "ded": "Sachsen", "dee": "Sachsen-Anhalt",
    "def": "Schleswig-Holstein", "deg": "Thüringen",
    # France NUTS2
    "fr10": "Île-de-France", "frb0": "Centre-Val de Loire", "frc1": "Bourgogne",
    "frc2": "Franche-Comté", "frd1": "Basse-Normandie", "frd2": "Haute-Normandie",
    "fre1": "Nord-Pas-de-Calais", "fre2": "Picardie", "frf1": "Alsace",
    "frf2": "Champagne-Ardenne", "frf3": "Lorraine", "frg0": "Pays de la Loire",
    "frh0": "Bretagne", "fri1": "Aquitaine", "fri2": "Limousin", "fri3": "Poitou-Charentes",
    "frj1": "Languedoc-Roussillon", "frj2": "Midi-Pyrénées", "frk1": "Auvergne",
    "frk2": "Rhône-Alpes", "frl0": "Provence-Alpes-Côte d'Azur", "frm0": "Corse",
    "fry1": "Guadeloupe", "fry2": "Martinique", "fry3": "Guyane", "fry4": "La Réunion",
    "fry5": "Mayotte",
    "frb": "Centre-Val de Loire", "frc": "Bourgogne-Franche-Comté",
    "frd": "Normandie", "fre": "Hauts-de-France", "frf": "Grand Est",
    "frg": "Pays de la Loire", "frh": "Bretagne", "fri": "Nouvelle-Aquitaine",
    "frj": "Occitanie", "frk": "Auvergne-Rhône-Alpes", "frl": "Provence-Alpes-Côte d'Azur",
    "frm": "Corse",
}

# Common NUTS3 / city codes seen in EURES
NUTS_CITY = {
    "ie061": "Dublin",
    "nl326": "Amsterdam", "nl327": "Hilversum", "nl329": "Amsterdam",
    "nl332": "The Hague", "nl333": "Rotterdam", "nl337": "The Hague",
    "nl310": "Utrecht", "nl31": "Utrecht",
    "nl414": "Eindhoven", "nl413": "Tilburg", "nl411": "Breda",
    "nl421": "Maastricht",
    "nl221": "Arnhem", "nl226": "Arnhem", "nl230": "Almere",
    "de300": "Berlin", "de600": "Hamburg", "de500": "Bremen",
    "fr101": "Paris", "fr105": "Paris", "fr107": "Paris",
}

REMOTE_RE = re.compile(
    r"(?i)(?<![\w-])(?:remote(?:ly)?|home[\s-]?office|homeoffice|tele[\s-]?work(?:ing)?|"
    r"télétravail|telewerken|thuiswerk(?:en)?|home[\s-]?office|arbeit[\s-]?im[\s-]?homeoffice|"
    r"home[\s-]?office|fernarbeit|mobiles? arbeiten)(?![\w-])"
)

start = time.time()
errors: list[str] = []
http_counts: dict[int, int] = {}
pages_by_cc: dict[str, int] = {cc: 0 for cc, _ in COUNTRIES}
jobs_by_cc: dict[str, int] = {cc: 0 for cc, _ in COUNTRIES}
last_week: dict[str, int | None] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    print(f"{now_iso()} {msg}", flush=True)


def remaining() -> float:
    return FETCH_SECONDS - (time.time() - start)


def polite_sleep() -> None:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


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


def loc_state_city(location_map) -> tuple[str, str]:
    if not isinstance(location_map, dict):
        return "", ""
    codes = []
    for _key, vals in location_map.items():
        if isinstance(vals, list):
            codes.extend(vals)
        elif vals:
            codes.append(vals)
    codes = [str(v).strip() for v in codes if v]
    state = ""
    city = ""
    # sort nuts keys longest-first
    nuts_keys = sorted(NUTS_STATE.keys(), key=len, reverse=True)
    city_keys = sorted(NUTS_CITY.keys(), key=len, reverse=True)
    for code in codes:
        cl = code.lower()
        if not city:
            for ck in city_keys:
                if cl == ck or cl.startswith(ck):
                    city = NUTS_CITY[ck]
                    break
        if not state:
            for nk in nuts_keys:
                if cl == nk or cl.startswith(nk):
                    state = NUTS_STATE[nk]
                    break
        if not city and not re.fullmatch(r"[a-z]{2}\w*", cl):
            city = code
    if city == "Dublin" and not state:
        state = "Dublin"
    return state, city


def is_remote(title: str, description: str, extra: str) -> bool:
    blob = " ".join(x for x in (title, description, extra) if x)
    return bool(REMOTE_RE.search(blob))


def job_url(jid: str, raw: dict) -> str:
    for key in ("url", "jobUrl", "jvUrl", "detailsUrl", "link"):
        val = raw.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
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
        "url": job_url(jid, raw),
        "posted_at": posted,
        "source": "eures",
        "description": desc,
    }


def save_raw(cc: str, page_n: int, obj) -> Path:
    path = RAW / f"eures_{cc}_p{page_n}.json"
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return path


def collect_country(cc: str, country_name: str, start_page: int = 1) -> None:
    page = start_page
    while page <= MAX_PAGE:
        if remaining() < 8:
            log(f"TIMEBOX stop cc={cc} page={page} left={remaining():.0f}s")
            return
        query = {
            "locationCodes": [cc],
            "publicationPeriod": "LAST_WEEK",
            "page": page,
            "resultsPerPage": PAGE_SIZE,
        }
        status, obj, err = http_json(query)
        if status != 200 or not isinstance(obj, dict):
            msg = f"FAIL cc={cc} page={page} status={status} err={(err or '')[:180]}"
            log(msg)
            errors.append(msg)
            if status in (400, 500) and page > 1:
                break
            # retry next page once on transient
            if status == 0:
                polite_sleep()
                page += 1
                continue
            break
        jvs = obj.get("jvs") if isinstance(obj.get("jvs"), list) else []
        total = obj.get("numberRecords")
        save_raw(cc, page, obj)
        pages_by_cc[cc] += 1
        jobs_by_cc[cc] += len(jvs)
        if page == start_page:
            last_week[cc] = total if isinstance(total, int) else None
        log(
            f"OK cc={cc} p{page} n={total} got={len(jvs)} "
            f"pages={pages_by_cc[cc]} jobs={jobs_by_cc[cc]} "
            f"elapsed={time.time()-start:.1f}s left={remaining():.0f}s"
        )
        if not jvs:
            break
        if isinstance(total, int) and page * PAGE_SIZE >= total:
            break
        if len(jvs) < PAGE_SIZE:
            break
        page += 1
        polite_sleep()


def normalize_all() -> dict:
    cc_to_country = {cc: name for cc, name in COUNTRIES}
    seen_urls: set[str] = set()
    written = 0
    remote_n = 0
    onsite_n = 0
    by_cc_written = {cc: 0 for cc in cc_to_country}
    skipped_no_id = 0
    dups = 0
    rows: list[dict] = []

    files = sorted(RAW.glob("eures_*_p*.json"), key=lambda p: p.name)
    for path in files:
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
        # accept both raw response and wrapped {response:...}
        if isinstance(payload, dict) and "jvs" in payload:
            resp = payload
        elif isinstance(payload, dict) and isinstance(payload.get("response"), dict):
            resp = payload["response"]
        else:
            continue
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

    return {
        "written": written,
        "remote": remote_n,
        "onsite": onsite_n,
        "dups_dropped": dups,
        "skipped_no_id": skipped_no_id,
        "by_country_written": by_cc_written,
        "pages_by_cc": pages_by_cc,
        "raw_jobs_seen": jobs_by_cc,
        "last_week_totals": last_week,
        "errors": errors,
        "http_counts": http_counts,
        "out": str(OUT),
        "elapsed_s": round(time.time() - start, 1),
    }


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    DEBUG.mkdir(parents=True, exist_ok=True)
    log("=== EURES collect start PAGE_SIZE=50 order=nl,fr,ie,de ===")

    # NL p1 already written with 50 jobs — count it, start at p2
    p1 = RAW / "eures_nl_p1.json"
    if p1.exists():
        try:
            obj = json.loads(p1.read_text(encoding="utf-8"))
            jvs = obj.get("jvs") or []
            pages_by_cc["nl"] = 1
            jobs_by_cc["nl"] = len(jvs)
            last_week["nl"] = obj.get("numberRecords")
            log(f"RESUME nl p1 already on disk got={len(jvs)} n={last_week['nl']}")
            collect_country("nl", "Netherlands", start_page=2)
        except Exception as e:
            log(f"p1 resume fail: {e}")
            collect_country("nl", "Netherlands", start_page=1)
    else:
        collect_country("nl", "Netherlands", start_page=1)

    for cc, name in COUNTRIES:
        if cc == "nl":
            continue
        if remaining() < 8:
            log(f"TIMEBOX skip {cc}")
            break
        log(f"=== COUNTRY {cc} {name} ===")
        collect_country(cc, name, start_page=1)

    log(f"FETCH END pages={pages_by_cc} jobs={jobs_by_cc} errors={len(errors)} elapsed={time.time()-start:.1f}s")

    summary = normalize_all()
    (RAW / "eures_collect_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"NORMALIZE written={summary['written']} remote={summary['remote']} onsite={summary['onsite']} path={OUT}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        DEBUG.mkdir(parents=True, exist_ok=True)
        with (DEBUG / "eures.txt").open("a", encoding="utf-8") as fh:
            fh.write(f"\nFATAL {now_iso()} {type(e).__name__}: {e}\n")
        raise

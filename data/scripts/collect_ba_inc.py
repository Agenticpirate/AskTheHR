#!/usr/bin/env python3
"""Incremental BA Jobsuche collector. Writes ba-jobsuche.jsonl as pages arrive."""
from __future__ import annotations

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
from typing import Any

ROOT = Path("/workspace/jobs")
RAW = ROOT / "raw"
NORM = ROOT / "normalized"
OUT = NORM / "ba-jobsuche.jsonl"
SEEN_PATH = RAW / "ba_seen_urls.txt"
LOG = RAW / "ba_inc_log.txt"
STATE = RAW / "ba_inc_state.json"

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
API_KEY = "jobboerse-jobsuche"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0; +https://www.arbeitsagentur.de)"
PAGE_SIZE = 100
MAX_PAGE = 250
SLEEP_MIN, SLEEP_MAX = 0.28, 0.48
TIMEOUT = 45

REGION_MAP = {
    "BADEN_WUERTTEMBERG": "Baden-Württemberg",
    "BAYERN": "Bayern",
    "BERLIN": "Berlin",
    "BRANDENBURG": "Brandenburg",
    "BREMEN": "Bremen",
    "HAMBURG": "Hamburg",
    "HESSEN": "Hessen",
    "MECKLENBURG_VORPOMMERN": "Mecklenburg-Vorpommern",
    "NIEDERSACHSEN": "Niedersachsen",
    "NORDRHEIN_WESTFALEN": "Nordrhein-Westfalen",
    "RHEINLAND_PFALZ": "Rheinland-Pfalz",
    "SAARLAND": "Saarland",
    "SACHSEN": "Sachsen",
    "SACHSEN_ANHALT": "Sachsen-Anhalt",
    "SCHLESWIG_HOLSTEIN": "Schleswig-Holstein",
    "THUERINGEN": "Thüringen",
}

REMOTE_RE = re.compile(
    r"home[\s\-]?office|remote|telearbeit|heimarbeit|heim-?\s*/?\s*telearbeit|"
    r"arbeit\s+von\s+zuhause|work[\s\-]?from[\s\-]?home|wfh|"
    r"homeofficemoeglich|mobil(e|es)?\s+arbeiten",
    re.I,
)

# Remote-ish first, then August DE volume via regional splits (pagination ~10k/query).
QUERIES: list[dict[str, Any]] = [
    {"pav": "true", "veroeffentlichtseit": 14},
    {"pav": "true"},
    {"was": "Homeoffice", "veroeffentlichtseit": 14},
    {"was": "Remote", "veroeffentlichtseit": 14},
    {"was": "Telearbeit", "veroeffentlichtseit": 14},
    {"was": "Heimarbeit", "veroeffentlichtseit": 14},
    {"veroeffentlichtseit": 14},
]

# Bundesländer + major cities to get past the ~10k pagination window.
WO_SLICES = [
    "Berlin", "Hamburg", "Bremen", "München", "Köln", "Frankfurt", "Stuttgart",
    "Düsseldorf", "Leipzig", "Dortmund", "Essen", "Dresden", "Hannover",
    "Nürnberg", "Duisburg", "Bochum", "Wuppertal", "Bielefeld", "Bonn",
    "Münster", "Karlsruhe", "Mannheim", "Augsburg", "Wiesbaden",
    "Gelsenkirchen", "Mönchengladbach", "Braunschweig", "Chemnitz", "Kiel",
    "Aachen", "Halle", "Magdeburg", "Freiburg", "Krefeld", "Lübeck",
    "Oberhausen", "Erfurt", "Mainz", "Rostock", "Kassel", "Hagen",
    "Saarbrücken", "Hamm", "Potsdam", "Ludwigshafen", "Oldenburg",
    "Osnabrück", "Leverkusen", "Heidelberg", "Darmstadt", "Regensburg",
    "Würzburg", "Göttingen", "Wolfsburg", "Heilbronn", "Pforzheim", "Ulm",
    "Ingolstadt", "Koblenz", "Trier", "Jena", "Erlangen", "Siegen",
    "Hildesheim", "Cottbus", "Kaiserslautern", "Gütersloh", "Schwerin",
    "Flensburg", "Passau", "Konstanz", "Bayreuth", "Bamberg", "Landshut",
    "Rosenheim", "Reutlingen", "Tübingen", "Offenburg", "Ludwigsburg",
    "Esslingen", "Fürth", "Aschaffenburg", "Kempten", "Schweinfurt",
    "Freising", "Paderborn", "Recklinghausen", "Bottrop", "Moers",
    "Bergisch Gladbach", "Remscheid", "Solingen", "Herne", "Neuss",
    "Mülheim", "Bayern", "Baden-Württemberg", "Nordrhein-Westfalen",
    "Niedersachsen", "Hessen", "Rheinland-Pfalz", "Sachsen",
    "Schleswig-Holstein", "Brandenburg", "Sachsen-Anhalt", "Thüringen",
    "Mecklenburg-Vorpommern", "Saarland",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{utc_now()} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def polite_sleep(mult: float = 1.0) -> None:
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX) * mult)


def build_url(params: dict[str, Any]) -> str:
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    return f"{BASE}?{q}"


def fetch_json(params: dict[str, Any]) -> tuple[int, Any, str]:
    url = build_url(params)
    last_err = ""
    for attempt in range(1, 8):
        req = urllib.request.Request(
            url,
            headers={
                "X-API-Key": API_KEY,
                "User-Agent": UA,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read()
                status = getattr(resp, "status", 200)
                data = json.loads(body.decode("utf-8"))
                return status, data, ""
        except urllib.error.HTTPError as exc:
            status = exc.code
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            last_err = f"HTTP {status}"
            try:
                err_body = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                err_body = ""
            if status in (429, 503) or (500 <= status < 600):
                wait = min(2 ** attempt, 60)
                if retry_after:
                    try:
                        wait = max(wait, float(retry_after))
                    except ValueError:
                        pass
                log(f"retry {attempt} {status} wait={wait:.1f}s {url} {err_body}")
                time.sleep(wait)
                continue
            log(f"error {status} {url} {err_body}")
            return status, None, last_err
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            wait = min(2 ** attempt, 25)
            log(f"retry {attempt} {last_err} wait={wait:.1f}s")
            time.sleep(wait)
    return 0, None, last_err


def hits_of(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ("ergebnisliste", "stellenangebote", "jobs"):
        val = payload.get(key)
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
    return []


def first_loc(hit: dict[str, Any]) -> dict[str, Any]:
    locs = hit.get("stellenlokationen") or hit.get("arbeitsorte") or []
    if isinstance(locs, list) and locs:
        loc0 = locs[0]
        if isinstance(loc0, dict):
            addr = loc0.get("adresse")
            if isinstance(addr, dict):
                return addr
            return loc0
    ao = hit.get("arbeitsort")
    if isinstance(ao, dict):
        return ao
    return {}


def pretty_region(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    key = s.upper().replace(" ", "_").replace("-", "_")
    if key in REGION_MAP and key != "DEUTSCHLAND":
        return REGION_MAP[key]
    if s.lower() in {"deutschland", "germany", "de"}:
        return ""
    return s.replace("_", "-").title() if s.isupper() else s


def posted_at(hit: dict[str, Any]) -> str:
    vz = hit.get("veroeffentlichungszeitraum")
    if isinstance(vz, dict) and vz.get("von"):
        return str(vz["von"])
    for key in (
        "aktuelleVeroeffentlichungsdatum",
        "datumErsteVeroeffentlichung",
        "aenderungsdatum",
    ):
        val = hit.get(key)
        if val:
            return str(val)[:10] if key == "aenderungsdatum" else str(val)
    ez = hit.get("eintrittszeitraum")
    if isinstance(ez, dict) and ez.get("von"):
        return str(ez["von"])
    if hit.get("eintrittsdatum"):
        return str(hit["eintrittsdatum"])
    return ""


def is_remote(hit: dict[str, Any], title: str, desc: str) -> bool:
    ho = hit.get("homeofficemoeglich")
    if ho is True or str(ho).lower() == "true":
        return True
    if hit.get("homeofficetyp") or hit.get("homeofficeprozent"):
        return True
    az = hit.get("arbeitszeit") or hit.get("arbeitszeitmodelle") or []
    if isinstance(az, str) and az.lower() in {"ho", "heim_telearbeit"}:
        return True
    if isinstance(az, list):
        joined = " ".join(str(x) for x in az).lower()
        if "heim" in joined or "tele" in joined or joined == "ho":
            return True
    blob = f"{title} {desc}"
    return bool(REMOTE_RE.search(blob))


def snippet(parts: list[str], n: int = 300) -> str:
    text = " — ".join(p.strip() for p in parts if p and str(p).strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


def job_url(hit: dict[str, Any], ref: str) -> str:
    for key in ("jobboerseUrl", "detailUrl", "url", "stellenangebotsUrl"):
        val = hit.get(key)
        if isinstance(val, str) and "arbeitsagentur.de" in val.lower():
            return val.strip()
    if ref:
        return f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}"
    return ""


def normalize_hit(hit: dict[str, Any]) -> dict[str, Any] | None:
    ref = str(hit.get("referenznummer") or hit.get("refnr") or "").strip()
    hid = str(hit.get("hashId") or "").strip()
    ident = ref or hid
    if not ident:
        return None
    title = str(
        hit.get("stellenangebotsTitel")
        or hit.get("titel")
        or hit.get("beruf")
        or ""
    ).strip()
    company = str(hit.get("firma") or hit.get("arbeitgeber") or "").strip()
    loc = first_loc(hit)
    city = str(loc.get("ort") or loc.get("city") or "").strip()
    state = pretty_region(loc.get("region") or loc.get("bundesland") or "")
    posted = posted_at(hit)
    url = job_url(hit, ref or hid)
    if not url:
        return None
    desc = snippet(
        [
            title,
            str(hit.get("hauptberuf") or hit.get("beruf") or ""),
            company,
            ", ".join(x for x in [city, state] if x),
            "Homeoffice möglich" if hit.get("homeofficemoeglich") is True else "",
            (
                f"Homeoffice {hit.get('homeofficeprozent')}%"
                if hit.get("homeofficeprozent")
                else str(hit.get("homeofficetyp") or "")
            ),
            str(hit.get("stellenangebotsart") or ""),
            str(hit.get("vertragsdauer") or ""),
        ]
    )
    remote = is_remote(hit, title, desc)
    return {
        "id": f"ba-jobsuche:{ident}",
        "title": title,
        "company": company,
        "country": "Germany",
        "state": state,
        "city": city,
        "remote": remote,
        "url": url,
        "posted_at": posted,
        "source": "ba-jobsuche",
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


def ingest_raw_files(seen: set[str]) -> int:
    added = 0
    files = sorted(
        list(RAW.glob("jobsuche_p*.json")) + list(RAW.glob("ba_p*.json")),
        key=lambda p: p.name,
    )
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows = []
        for hit in hits_of(payload):
            row = normalize_hit(hit)
            if row:
                rows.append(row)
        added += append_jobs(rows, seen)
    return added


def collect_query(q: dict[str, Any], seen: set[str], tag: str) -> tuple[int, int, int]:
    pages = 0
    raw_n = 0
    written = 0
    page = 1
    while page <= MAX_PAGE:
        params = dict(q)
        params["size"] = PAGE_SIZE
        params["page"] = page
        status, payload, err = fetch_json(params)
        if payload is None:
            log(f"FAIL {tag} page={page} {err}")
            break
        pages += 1
        hs = hits_of(payload)
        max_e = payload.get("maxErgebnisse")
        raw_n += len(hs)
        rows = []
        for hit in hs:
            row = normalize_hit(hit)
            if row:
                rows.append(row)
        w = append_jobs(rows, seen)
        written += w
        if page == 1 or page % 10 == 0 or not hs:
            log(
                f"OK {tag} page={page} max={max_e} hits={len(hs)} wrote={w} "
                f"file_total={len(seen)} http={status}"
            )
        if not hs:
            break
        if len(hs) < PAGE_SIZE:
            break
        if isinstance(max_e, int) and page * PAGE_SIZE >= max_e:
            break
        page += 1
        polite_sleep()
    return pages, raw_n, written


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    log("=== BA incremental collect start ===")
    seen = load_seen()
    log(f"resume seen={len(seen)} out={OUT}")
    ingested = ingest_raw_files(seen)
    log(f"ingested existing raw wrote={ingested} seen={len(seen)}")

    # Probe working filters
    status, probe, err = fetch_json({"size": 1, "page": 1})
    if probe:
        log(f"PROBE unfiltered maxErgebnisse={probe.get('maxErgebnisse')} status={status}")
    polite_sleep()
    status, probe, err = fetch_json({"size": 1, "page": 1, "pav": "true"})
    if probe:
        log(f"PROBE pav=true maxErgebnisse={probe.get('maxErgebnisse')} status={status}")

    done_keys: set[str] = set()
    if STATE.exists():
        try:
            done_keys = set(json.loads(STATE.read_text()).get("done") or [])
        except Exception:
            done_keys = set()

    def mark(key: str) -> None:
        done_keys.add(key)
        STATE.write_text(json.dumps({"done": sorted(done_keys), "seen": len(seen)}, indent=2), encoding="utf-8")

    # 1) remote-ish + august national
    for q in QUERIES:
        key = json.dumps(q, sort_keys=True)
        if key in done_keys:
            log(f"SKIP done {q}")
            continue
        log(f"QUERY start {q}")
        pages, raw_n, written = collect_query(q, seen, tag=str(q))
        log(f"QUERY done {q} pages={pages} raw={raw_n} wrote={written} seen={len(seen)}")
        mark(key)
        polite_sleep()

    # 2) regional August slices to break the pagination window
    for wo in WO_SLICES:
        q = {"wo": wo, "veroeffentlichtseit": 14}
        key = json.dumps(q, sort_keys=True)
        if key in done_keys:
            continue
        log(f"QUERY start {q}")
        pages, raw_n, written = collect_query(q, seen, tag=f"wo={wo}")
        log(f"QUERY done wo={wo} pages={pages} raw={raw_n} wrote={written} seen={len(seen)}")
        mark(key)
        polite_sleep()

    # 3) more days / broader if still going
    for days in (7, 21, 31, 45, 60, 100):
        q = {"veroeffentlichtseit": days}
        key = json.dumps(q, sort_keys=True)
        if key in done_keys:
            continue
        log(f"QUERY start {q}")
        pages, raw_n, written = collect_query(q, seen, tag=str(q))
        log(f"QUERY done {q} pages={pages} raw={raw_n} wrote={written} seen={len(seen)}")
        mark(key)

    # Re-ingest any new raw pages from the other collector
    extra = ingest_raw_files(seen)
    log(f"final re-ingest wrote={extra} seen={len(seen)}")
    log(f"=== BA collect done seen={len(seen)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

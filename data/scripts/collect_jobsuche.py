#!/usr/bin/env python3
"""Collect BA Jobsuche v6 public listings, then write normalized JSONL."""

from __future__ import annotations

import json
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
LOG_PATH = RAW / "jobsuche_log.txt"
NORM_PATH = NORM / "jobsuche.jsonl"

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
API_KEY = "jobboerse-jobsuche"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
PAGE_SIZE = 100
SLEEP_S = 0.40
TIME_BUDGET_S = 12 * 60
MAX_RETRIES = 6

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
    "DEUTSCHLAND": "Germany",
}

REMOTE_RE = re.compile(
    r"home[\s\-]?office|remote|telearbeit|heimarbeit|heim-?\s*/?\s*telearbeit|"
    r"arbeit\s+von\s+zuhause|work[\s\-]?from[\s\-]?home|wfh|"
    r"homeofficemoeglich|mobil(e|es)?\s+arbeiten",
    re.I,
)

QUERIES: list[dict[str, Any]] = [
    {"was": "Homeoffice", "veroeffentlichtseit": 14},
    {"was": "Remote", "veroeffentlichtseit": 14},
    {"was": "Telearbeit", "veroeffentlichtseit": 14},
    {"was": "Heimarbeit", "veroeffentlichtseit": 14},
    {"was": "Home-Office", "veroeffentlichtseit": 14},
    {"pav": "true", "veroeffentlichtseit": 14},
    {"veroeffentlichtseit": 7, "angebotsart": 1},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{utc_now()} {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def build_url(params: dict[str, Any]) -> str:
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    return f"{BASE}?{q}"


def fetch_json(params: dict[str, Any]) -> tuple[int, Any, str]:
    url = build_url(params)
    last_err = ""
    for attempt in range(1, MAX_RETRIES + 1):
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
            with urllib.request.urlopen(req, timeout=45) as resp:
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
                wait = 2 ** attempt
                if retry_after:
                    try:
                        wait = max(wait, float(retry_after))
                    except ValueError:
                        pass
                wait = min(wait, 45)
                log(f"retry {attempt}/{MAX_RETRIES} {status} wait={wait:.1f}s {url} {err_body}")
                time.sleep(wait)
                continue
            log(f"error {status} {url} {err_body}")
            return status, None, last_err
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            wait = min(2 ** attempt, 20)
            log(f"retry {attempt}/{MAX_RETRIES} {last_err} wait={wait:.1f}s {url}")
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


def collect() -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {
        "probe": {},
        "pages": 0,
        "raw_hits": 0,
        "errors": [],
        "queries": [],
        "started_at": utc_now(),
    }

    log("PROBE size=1 unfiltered")
    time.sleep(SLEEP_S)
    status, probe, err = fetch_json({"size": 1})
    if probe is None:
        stats["errors"].append(f"probe failed: {err}")
        log(f"PROBE failed {err}")
    else:
        (RAW / "jobsuche_probe.json").write_text(
            json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        stats["probe"] = {
            "status": status,
            "size": probe.get("size"),
            "page": probe.get("page"),
            "maxErgebnisse": probe.get("maxErgebnisse"),
            "pagination_param": "page",
            "hit_list_key": "ergebnisliste",
            "top_keys": list(probe.keys()),
        }
        log(
            f"PROBE ok size={probe.get('size')} page={probe.get('page')} "
            f"maxErgebnisse={probe.get('maxErgebnisse')} pagination=page "
            f"list=ergebnisliste"
        )

    log(f"PROBE size={PAGE_SIZE} Homeoffice+14d")
    time.sleep(SLEEP_S)
    status, probe100, err = fetch_json(
        {"was": "Homeoffice", "veroeffentlichtseit": 14, "size": PAGE_SIZE, "page": 1}
    )
    if probe100:
        stats["probe"]["size_used"] = probe100.get("size")
        stats["probe"]["homeoffice_14d_total"] = probe100.get("maxErgebnisse")
        log(
            f"PROBE size_used={probe100.get('size')} hits={len(hits_of(probe100))} "
            f"homeoffice_14d_total={probe100.get('maxErgebnisse')}"
        )
    else:
        stats["errors"].append(f"size probe failed: {err}")

    deadline = time.monotonic() + TIME_BUDGET_S
    page_n = 0

    for q in QUERIES:
        if time.monotonic() >= deadline:
            log("TIMEBOX reached before query " + json.dumps(q, ensure_ascii=False))
            break
        qstats = {"query": q, "pages": 0, "hits": 0, "maxErgebnisse": None, "stopped": ""}
        page = 1
        log(f"QUERY start {q}")
        while time.monotonic() < deadline:
            params = dict(q)
            params["size"] = PAGE_SIZE
            params["page"] = page
            time.sleep(SLEEP_S)
            status, payload, err = fetch_json(params)
            if payload is None:
                stats["errors"].append(f"page={page} q={q} {err}")
                qstats["stopped"] = f"error {err}"
                break
            page_n += 1
            raw_path = RAW / f"jobsuche_p{page_n}.json"
            raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            hs = hits_of(payload)
            max_e = payload.get("maxErgebnisse")
            qstats["maxErgebnisse"] = max_e
            qstats["pages"] += 1
            qstats["hits"] += len(hs)
            stats["pages"] += 1
            stats["raw_hits"] += len(hs)
            log(
                f"SAVED {raw_path.name} q={q} api_page={page} "
                f"hits={len(hs)} max={max_e} http={status}"
            )
            if not hs:
                qstats["stopped"] = "empty"
                break
            if len(hs) < PAGE_SIZE:
                qstats["stopped"] = "short_page"
                break
            if isinstance(max_e, int) and page * PAGE_SIZE >= max_e:
                qstats["stopped"] = "exhausted"
                break
            page += 1
        else:
            qstats["stopped"] = "timebox"
            log(f"TIMEBOX during query {q} after api_page={page}")
        stats["queries"].append(qstats)
        log(f"QUERY done {q} pages={qstats['pages']} hits={qstats['hits']} stop={qstats['stopped']}")

    stats["finished_at"] = utc_now()
    stats["page_files"] = page_n
    return stats


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
    country_raw = str(loc.get("land") or "").strip()
    country = "Germany"
    if country_raw and country_raw.upper() not in {"DEUTSCHLAND", "GERMANY", "DE", ""}:
        # still label Germany: this is the BA DE board
        country = "Germany"
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
            (
                "Homeoffice möglich"
                if hit.get("homeofficemoeglich") is True
                else ""
            ),
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
        "id": f"jobsuche:{ident}",
        "title": title,
        "company": company,
        "country": country,
        "state": state,
        "city": city,
        "remote": remote,
        "url": url,
        "posted_at": posted,
        "source": "jobsuche",
        "description": desc,
    }


def canon_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    p = urllib.parse.urlparse(raw)
    return urllib.parse.urlunparse(
        (p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", "", "")
    )


def normalize_all() -> dict[str, Any]:
    files = sorted(
        RAW.glob("jobsuche_p*.json"),
        key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)) if re.search(r"(\d+)", p.stem) else 0,
    )
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    skipped = 0
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log(f"normalize skip {path.name}: {exc}")
            continue
        for hit in hits_of(payload):
            row = normalize_hit(hit)
            if not row:
                skipped += 1
                continue
            key = canon_url(row["url"])
            if not key or key in seen:
                skipped += 1
                continue
            seen.add(key)
            rows.append(row)
    NORM.mkdir(parents=True, exist_ok=True)
    with NORM_PATH.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
    remote_n = sum(1 for r in rows if r["remote"])
    stats = {
        "written": len(rows),
        "remote": remote_n,
        "onsite": len(rows) - remote_n,
        "skipped_or_dup": skipped,
        "files": len(files),
        "path": str(NORM_PATH),
    }
    log(f"NORMALIZE {stats}")
    return stats


def main() -> int:
    LOG_PATH.write_text("", encoding="utf-8")
    log("START jobsuche collector")
    col = collect()
    norm = normalize_all()
    summary = {"collect": col, "normalize": norm}
    (RAW / "jobsuche_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log("DONE")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

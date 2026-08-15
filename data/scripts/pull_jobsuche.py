#!/usr/bin/env python3
"""BA Jobsuche volume pull: resume Homeoffice+14d, then d14, then full catalog."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

ROOT = Path("/workspace/jobs")
RAW = ROOT / "raw"
NORM = ROOT / "normalized"
SCRIPT_LOG = RAW / "pull_jobsuche_log.txt"
NORM_PATH = NORM / "jobsuche.jsonl"
COMBINED = ROOT / "remote-aug2026.jsonl"
SUMMARY = ROOT / "summary.json"

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
API_KEY = "jobboerse-jobsuche"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
PAGE_SIZE = 100
SLEEP_S = 0.30
TIME_BUDGET_S = 12 * 60
MAX_RETRIES = 5
INGEST_EVERY = 10_000
PAGE_CAP = 120

CITIES = [
    "Berlin", "München", "Hamburg", "Köln", "Frankfurt", "Stuttgart",
    "Düsseldorf", "Leipzig", "Dortmund", "Essen", "Bremen", "Dresden",
    "Hannover", "Nürnberg",
]
KEYWORDS = [
    "Informatik", "Pflege", "Verkauf", "Ingenieur", "Büro", "Lager",
    "Produktion", "Handwerk", "Lehrer", "Arzt", "Fahrer", "Koch",
    "Reinigung", "Sicherheit", "Management", "Vertrieb", "Buchhaltung",
    "Elektriker", "Mechaniker", "Bau", "IT", "Sachbearbeiter",
    "Kundenberater", "Logistik", "Erzieher", "Arzt", "Krankenpflege",
    "Software", "Projekt", "Assistenz", "Service",
]

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
    r"home[\s\-]?office|remote|telearbeit|heimarbeit|homeofficemoeglich|"
    r"arbeit\s+von\s+zuhause|work[\s\-]?from[\s\-]?home|wfh|"
    r"mobil(e|es)?\s+arbeiten",
    re.I,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{utc_now()} {msg}"
    print(line, flush=True)
    SCRIPT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SCRIPT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def slug(s: str) -> str:
    t = (
        s.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t or "x"


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
            with urllib.request.urlopen(req, timeout=40) as resp:
                body = resp.read()
                status = getattr(resp, "status", 200)
                return status, json.loads(body.decode("utf-8")), ""
        except urllib.error.HTTPError as exc:
            status = exc.code
            last_err = f"HTTP {status}"
            try:
                err_body = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                err_body = ""
            if status in (429, 503) or 500 <= status < 600:
                wait = min(2 ** attempt, 30)
                log(f"retry {attempt} {status} wait={wait}s {url} {err_body}")
                time.sleep(wait)
                continue
            log(f"error {status} {url} {err_body}")
            return status, None, last_err
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            wait = min(2 ** attempt, 15)
            log(f"retry {attempt} {last_err} wait={wait}s")
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
    ao = hit.get("arbeitsort")
    if isinstance(ao, dict) and (ao.get("ort") or ao.get("region")):
        return ao
    locs = hit.get("stellenlokationen") or hit.get("arbeitsorte") or []
    if isinstance(locs, list) and locs:
        loc0 = locs[0]
        if isinstance(loc0, dict):
            addr = loc0.get("adresse")
            if isinstance(addr, dict):
                return addr
            return loc0
    return {}


def pretty_region(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    key = s.upper().replace(" ", "_").replace("-", "_")
    if key in REGION_MAP:
        return REGION_MAP[key]
    if s.lower() in {"deutschland", "germany", "de"}:
        return ""
    return s.replace("_", "-").title() if s.isupper() else s


THIS_MONTH_PREFIX = "2026-08"


def _date_only(val: Any) -> str:
    if not val:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    # 2026-08-14 or 2026-08-14T... or 14.08.2026
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    if len(s) >= 10:
        return s[:10]
    return s


def posted_at(hit: dict[str, Any]) -> str:
    """Always return a posted_at date. Never empty. Do not drop older dates."""
    vz = hit.get("veroeffentlichungszeitraum")
    if isinstance(vz, dict):
        d = _date_only(vz.get("von") or vz.get("bis"))
        if d:
            return d
    for key in (
        "aktuelleVeroeffentlichungsdatum",
        "datumErsteVeroeffentlichung",
        "ersteVeroeffentlichungsdatum",
        "aenderungsdatum",
        "modifikationsTimestamp",
        "eintrittsdatum",
    ):
        d = _date_only(hit.get(key))
        if d:
            return d
    ez = hit.get("eintrittszeitraum")
    if isinstance(ez, dict):
        d = _date_only(ez.get("von") or ez.get("bis"))
        if d:
            return d
    # last resort: keep the job, stamp today so posted_at is never blank
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def is_this_month(posted: str) -> bool:
    return (posted or "").startswith(THIS_MONTH_PREFIX)


def is_remote(hit: dict[str, Any], title: str, desc: str) -> bool:
    ho = hit.get("homeofficemoeglich")
    if ho is True or str(ho).lower() == "true":
        return True
    if hit.get("homeofficetyp") or hit.get("homeofficeprozent"):
        return True
    return bool(REMOTE_RE.search(f"{title} {desc}"))


def snippet(parts: list[str], n: int = 300) -> str:
    text = " — ".join(p.strip() for p in parts if p and str(p).strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


def normalize_hit(hit: dict[str, Any]) -> dict[str, Any] | None:
    ref = str(hit.get("referenznummer") or hit.get("refnr") or "").strip()
    hid = str(hit.get("hashId") or "").strip()
    ident = ref or hid
    if not ident:
        return None
    title = str(
        hit.get("stellenangebotsTitel") or hit.get("titel") or hit.get("beruf") or ""
    ).strip()
    company = str(hit.get("arbeitgeber") or hit.get("firma") or "").strip()
    loc = first_loc(hit)
    city = str(loc.get("ort") or loc.get("city") or "").strip()
    state = pretty_region(loc.get("region") or loc.get("bundesland") or "")
    posted = posted_at(hit) or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ident}"
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
        ]
    )
    remote = is_remote(hit, title, desc)
    return {
        "id": f"jobsuche:{ident}",
        "title": title,
        "company": company,
        "country": "Germany",
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
    p = urlparse(raw)
    return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", "", ""))


def highest_existing(pattern_prefix: str) -> int:
    mx = 0
    for p in RAW.glob(f"{pattern_prefix}*.json"):
        m = re.search(r"_p(\d+)\.json$", p.name)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx


def ho_done() -> tuple[bool, int]:
    mx = 0
    last_hits = 0
    last_max = 0
    for p in RAW.glob("jobsuche_p*.json"):
        m = re.search(r"jobsuche_p(\d+)\.json$", p.name)
        if not m:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("maxErgebnisse") != 8707 and data.get("page") != int(m.group(1)):
            # other-query files after HO
            if int(m.group(1)) <= 88 and data.get("maxErgebnisse") == 8707:
                pass
            else:
                continue
        if data.get("maxErgebnisse") == 8707:
            n = int(m.group(1))
            if n > mx:
                mx = n
                last_hits = len(hits_of(data))
                last_max = data.get("maxErgebnisse") or 0
    if mx >= 88 and last_hits < PAGE_SIZE:
        return True, mx
    if mx and last_max and mx * PAGE_SIZE >= last_max:
        return True, mx
    return mx >= 88, mx


class Ingest:
    def __init__(self) -> None:
        self.js_seen: set[str] = set()
        self.js_written = 0
        self.new_since_ingest = 0
        self.pages_since_ingest = 0
        self.total_pages = 0
        self.total_raw_hits = 0
        self.errors: list[str] = []
        NORM.mkdir(parents=True, exist_ok=True)
        if NORM_PATH.exists():
            with NORM_PATH.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    u = canon_url(row.get("url") or "")
                    i = row.get("id") or ""
                    if u:
                        self.js_seen.add(u)
                    if i:
                        self.js_seen.add(i)
                    self.js_written += 1
        self.combined_rows: list[dict[str, Any]] | None = None
        self.combined_by_url: dict[str, int] | None = None

    def load_combined(self) -> None:
        rows: list[dict[str, Any]] = []
        by: dict[str, int] = {}
        if COMBINED.exists():
            with COMBINED.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    u = canon_url(row.get("url") or "")
                    if not u:
                        continue
                    if u in by:
                        rows[by[u]] = row
                    else:
                        by[u] = len(rows)
                        rows.append(row)
        self.combined_rows = rows
        self.combined_by_url = by

    def append_hits(self, hits: list[dict[str, Any]]) -> int:
        added = 0
        if not hits:
            return 0
        with NORM_PATH.open("a", encoding="utf-8") as fh:
            for hit in hits:
                row = normalize_hit(hit)
                if not row:
                    continue
                u = canon_url(row["url"])
                if not u or u in self.js_seen or row["id"] in self.js_seen:
                    continue
                self.js_seen.add(u)
                self.js_seen.add(row["id"])
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
                added += 1
                self.js_written += 1
                self.new_since_ingest += 1
        return added

    def maybe_rewrite(self, force: bool = False) -> None:
        if not force and self.new_since_ingest < INGEST_EVERY:
            return
        if self.new_since_ingest <= 0 and not force:
            return
        log(f"INGEST rewrite new={self.new_since_ingest} js_total={self.js_written} force={force}")
        if self.combined_rows is None:
            self.load_combined()
        assert self.combined_rows is not None and self.combined_by_url is not None
        # fold current jobsuche.jsonl into combined
        if NORM_PATH.exists():
            with NORM_PATH.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    u = canon_url(row.get("url") or "")
                    if not u:
                        continue
                    if u in self.combined_by_url:
                        self.combined_rows[self.combined_by_url[u]] = row
                    else:
                        self.combined_by_url[u] = len(self.combined_rows)
                        self.combined_rows.append(row)
        by_source: Counter[str] = Counter()
        by_country: Counter[str] = Counter()
        remote_n = 0
        onsite_n = 0
        this_month = 0
        older_active = 0
        month_rows: list[dict[str, Any]] = []
        for row in self.combined_rows:
            # never drop older; fill blank posted_at
            posted = str(row.get("posted_at") or "").strip()
            if not posted:
                posted = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                row["posted_at"] = posted
            by_source[str(row.get("source") or "")] += 1
            by_country[str(row.get("country") or "")] += 1
            if row.get("remote") is True:
                remote_n += 1
            else:
                onsite_n += 1
            if is_this_month(posted):
                this_month += 1
                month_rows.append(row)
            else:
                older_active += 1
        tmp = COMBINED.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for row in self.combined_rows:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
        tmp.replace(COMBINED)
        month_path = ROOT / "remote-aug2026-thismonth.jsonl"
        mtmp = month_path.with_suffix(".jsonl.tmp")
        with mtmp.open("w", encoding="utf-8") as fh:
            for row in month_rows:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
        mtmp.replace(month_path)
        summary = {
            "total": len(self.combined_rows),
            "this_month": this_month,
            "older_active": older_active,
            "by_source": dict(sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_country": dict(sorted(by_country.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_remote": {"remote": remote_n, "onsite": onsite_n},
            "updated_at": utc_now(),
            "jobsuche_jsonl": self.js_written,
            "pages_this_run": self.total_pages,
            "raw_hits_this_run": self.total_raw_hits,
            "thismonth_path": str(month_path),
        }
        SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"INGEST done total={summary['total']} this_month={this_month} older_active={older_active} jobsuche={by_source.get('jobsuche', 0)}")
        self.new_since_ingest = 0
        self.pages_since_ingest = 0


def page_series(
    ingest: Ingest,
    deadline: float,
    params_base: dict[str, Any],
    file_prefix: str,
    start_page: int | None = None,
) -> dict[str, Any]:
    """Page a query. file_prefix e.g. jobsuche_d14 or jobsuche_all_berlin."""
    RAW.mkdir(parents=True, exist_ok=True)
    existing_max = highest_existing(file_prefix + "_p")
    page = start_page if start_page is not None else (existing_max + 1 if existing_max else 1)
    stats = {
        "prefix": file_prefix,
        "query": dict(params_base),
        "start_page": page,
        "pages": 0,
        "hits": 0,
        "added": 0,
        "maxErgebnisse": None,
        "stopped": "",
        "last_page": page - 1,
    }
    log(f"SERIES start {file_prefix} page={page} q={params_base} existing_max={existing_max}")
    while time.monotonic() < deadline:
        if page > PAGE_CAP:
            stats["stopped"] = "page_cap"
            break
        out = RAW / f"{file_prefix}_p{page}.json"
        payload = None
        status = 0
        if out.exists():
            try:
                payload = json.loads(out.read_text(encoding="utf-8"))
                status = 200
                log(f"SKIP existing {out.name}")
            except Exception:
                payload = None
        if payload is None:
            params = dict(params_base)
            params["size"] = PAGE_SIZE
            params["page"] = page
            time.sleep(SLEEP_S)
            status, payload, err = fetch_json(params)
            if payload is None:
                ingest.errors.append(f"{file_prefix} p{page} {err}")
                stats["stopped"] = f"error {err}"
                break
            out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        hs = hits_of(payload)
        max_e = payload.get("maxErgebnisse")
        stats["maxErgebnisse"] = max_e
        stats["pages"] += 1
        stats["hits"] += len(hs)
        stats["last_page"] = page
        ingest.total_pages += 1
        ingest.total_raw_hits += len(hs)
        ingest.pages_since_ingest += 1
        added = ingest.append_hits(hs)
        stats["added"] += added
        log(
            f"SAVED {out.name} api_page={payload.get('page')} hits={len(hs)} "
            f"added={added} max={max_e} http={status} js={ingest.js_written}"
        )
        ingest.maybe_rewrite(force=False)
        if not hs:
            stats["stopped"] = "empty"
            break
        if len(hs) < PAGE_SIZE:
            stats["stopped"] = "short_page"
            break
        if isinstance(max_e, int) and page * PAGE_SIZE >= max_e:
            stats["stopped"] = "exhausted"
            break
        page += 1
    else:
        stats["stopped"] = "timebox"
    log(
        f"SERIES done {file_prefix} pages={stats['pages']} hits={stats['hits']} "
        f"added={stats['added']} stop={stats['stopped']} max={stats['maxErgebnisse']}"
    )
    return stats


def run() -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + TIME_BUDGET_S
    ingest = Ingest()
    log(f"START pull_jobsuche js_existing={ingest.js_written}")

    series_stats: list[dict[str, Any]] = []

    done, ho_max = ho_done()
    log(f"HO status done={done} max_file={ho_max}")
    log("FOLD existing jobsuche raw pages into jobsuche.jsonl")
    files = sorted(RAW.glob("jobsuche*.json"), key=lambda p: p.name)
    folded = 0
    for path in files:
        if path.name in {"jobsuche_log.txt", "jobsuche_probe.json", "jobsuche_run_summary.json"}:
            continue
        if not path.name.endswith(".json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict) or not hits_of(payload):
            continue
        folded += ingest.append_hits(hits_of(payload))
    log(f"FOLD done added={folded} js={ingest.js_written}")
    ingest.maybe_rewrite(force=ingest.new_since_ingest > 0)
    if not done:
        st = page_series(
            ingest,
            deadline,
            {"was": "Homeoffice", "veroeffentlichtseit": 14},
            "jobsuche",
            start_page=ho_max + 1 if ho_max else 1,
        )
        series_stats.append(st)

    # d14 already moving on disk — keep full BA catalog first
    d14_n = highest_existing("jobsuche_d14_p")
    log(f"d14 existing pages={d14_n} -> full catalog first")

    if time.monotonic() < deadline:
        st = page_series(ingest, deadline, {}, "jobsuche_all")
        series_stats.append(st)
        need_split = st["stopped"] != "exhausted"
        if need_split and time.monotonic() < deadline:
            max_e = st.get("maxErgebnisse")
            if not max_e or (isinstance(max_e, int) and max_e < 500000 and st["stopped"] != "timebox"):
                st2 = page_series(
                    ingest, deadline, {"veroeffentlichtseit": 100}, "jobsuche_all_v100"
                )
                series_stats.append(st2)
            for city in CITIES:
                if time.monotonic() >= deadline:
                    break
                stc = page_series(
                    ingest, deadline, {"wo": city}, f"jobsuche_all_{slug(city)}"
                )
                series_stats.append(stc)
            for kw in KEYWORDS:
                if time.monotonic() >= deadline:
                    break
                stk = page_series(
                    ingest, deadline, {"was": kw}, f"jobsuche_all_kw_{slug(kw)}"
                )
                series_stats.append(stk)

    # continue d14 if time remains (do not overwrite existing)
    if time.monotonic() < deadline:
        st = page_series(
            ingest, deadline, {"veroeffentlichtseit": 14}, "jobsuche_d14"
        )
        series_stats.append(st)
        if time.monotonic() < deadline:
            for city in CITIES:
                if time.monotonic() >= deadline:
                    break
                stc = page_series(
                    ingest,
                    deadline,
                    {"veroeffentlichtseit": 14, "wo": city},
                    f"jobsuche_d14_{slug(city)}",
                )
                series_stats.append(stc)

    ingest.maybe_rewrite(force=True)
    out = {
        "started": True,
        "finished_at": utc_now(),
        "pages": ingest.total_pages,
        "raw_hits": ingest.total_raw_hits,
        "jobsuche_jsonl": ingest.js_written,
        "errors": ingest.errors,
        "series": series_stats,
        "ingest_total": None,
    }
    if SUMMARY.exists():
        try:
            out["ingest_total"] = json.loads(SUMMARY.read_text(encoding="utf-8")).get("total")
        except Exception:
            pass
    (RAW / "pull_jobsuche_run.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(f"DONE pages={out['pages']} raw_hits={out['raw_hits']} js={out['jobsuche_jsonl']} ingest={out['ingest_total']}")
    return out


def main() -> int:
    try:
        run()
    except Exception as exc:
        log(f"FATAL {type(exc).__name__}: {exc}")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())

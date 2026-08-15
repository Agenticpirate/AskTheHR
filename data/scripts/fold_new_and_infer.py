#!/usr/bin/env python3
"""Fold new raw pages into normalized JSONL, apply state-infer, rewrite ingest.

No API fetches. Uses state-infer.json only for city→state backfill.
"""
from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path("/workspace/jobs")
RAW = ROOT / "raw"
NORM = ROOT / "normalized"
STATE_PATH = ROOT / "state-infer.json"
COMBINED = ROOT / "remote-aug2026.jsonl"
SUMMARY = ROOT / "summary.json"
ALL_PATH = NORM / "all.jsonl"
HIMALAYAS_PATH = NORM / "himalayas.jsonl"
MCF_OUT = NORM / "mycareersfuture.jsonl"
JS_OUT = NORM / "jobsuche.jsonl"

ALLOWED = {
    "USA", "India", "Canada", "UK", "Australia",
    "Germany", "Netherlands", "Ireland", "Singapore", "France",
}
COUNTRY_ORDER = (
    "USA", "India", "Canada", "UK", "Australia",
    "Germany", "Netherlands", "Ireland", "Singapore", "France",
)
SCHEMA = (
    "id", "title", "company", "country", "state", "city",
    "remote", "url", "posted_at", "source", "description",
)

MCF_REMOTE_RE = re.compile(
    r"remote|work[\s\-]*from[\s\-]*home|flexi[\s\-]*place|wfh|"
    r"telecommut|home[\s\-]*based|work[\s\-]*at[\s\-]*home|"
    r"hybrid[\s\-]*remote|\bfrom home\b",
    re.I,
)
JS_REMOTE_RE = re.compile(
    r"home[\s\-]?office|remote|telearbeit|heimarbeit|heim-?\s*/?\s*telearbeit|"
    r"arbeit\s+von\s+zuhause|work[\s\-]?from[\s\-]?home|wfh|"
    r"homeofficemoeglich|mobil(e|es)?\s+arbeiten",
    re.I,
)
JS_REGION_MAP = {
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


def canon_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")
        ]
    )
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, host, path, parsed.params, query, parsed.fragment))


def fold_text(value: object) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_json(path: Path):
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
    tmp.replace(path)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def project(row: dict) -> dict:
    posted = row.get("posted_at")
    if posted is not None and not isinstance(posted, str):
        posted = str(posted)
    remote = row.get("remote")
    if isinstance(remote, bool):
        rem = remote
    else:
        rem = str(remote or "").strip().lower() in {"1", "true", "yes", "remote", "y"}
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or ""),
        "company": str(row.get("company") or ""),
        "country": str(row.get("country") or ""),
        "state": str(row.get("state") or ""),
        "city": str(row.get("city") or ""),
        "remote": rem,
        "url": str(row.get("url") or "").strip(),
        "posted_at": posted if posted is not None else "",
        "source": str(row.get("source") or ""),
        "description": str(row.get("description") or ""),
    }


# ---- MyCareersFuture ----
def mcf_company(job: dict) -> str:
    for key in ("postedCompany", "hiringCompany", "company"):
        obj = job.get(key)
        if isinstance(obj, dict) and obj.get("name"):
            return str(obj["name"]).strip()
        if isinstance(obj, str) and obj.strip():
            return obj.strip()
    return ""


def mcf_city(job: dict) -> str:
    addr = job.get("address")
    if not isinstance(addr, dict):
        return ""
    districts = addr.get("districts") or []
    if isinstance(districts, list) and districts:
        d0 = districts[0]
        if isinstance(d0, dict):
            loc = str(d0.get("location") or "").strip()
            if loc:
                return loc
    parts = []
    for k in ("building", "street", "block"):
        v = addr.get(k)
        if v:
            parts.append(str(v).strip())
    if addr.get("overseasCountry"):
        parts.append(str(addr["overseasCountry"]).strip())
    return ", ".join(p for p in parts if p)


def mcf_remote(job: dict) -> bool:
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
    return bool(blob and MCF_REMOTE_RE.search(blob))


def mcf_url(job: dict) -> str:
    md = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    url = (md.get("jobDetailsUrl") or "").strip()
    if url:
        return url
    uid = job.get("uuid") or job.get("id") or ""
    if uid:
        return f"https://www.mycareersfuture.gov.sg/job/{uid}"
    return ""


def mcf_id(job: dict) -> str:
    uid = job.get("uuid") or job.get("id")
    if not uid:
        md = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
        uid = md.get("jobPostId")
    if not uid:
        return ""
    return f"mycareersfuture:{uid}"


def normalize_mcf_job(job: dict) -> dict | None:
    if not isinstance(job, dict):
        return None
    url = mcf_url(job)
    jid = mcf_id(job)
    title = str(job.get("title") or "").strip()
    if not url or not jid or not title:
        return None
    md = job.get("metadata") if isinstance(job.get("metadata"), dict) else {}
    posted = str(md.get("newPostingDate") or "")
    return {
        "id": jid,
        "title": title,
        "company": mcf_company(job),
        "country": "Singapore",
        "state": "",  # Singapore has no state
        "city": mcf_city(job),
        "remote": mcf_remote(job),
        "url": url,
        "posted_at": posted,
        "source": "mycareersfuture",
        "description": short_desc(job.get("description") or job.get("jobDescription") or "", 300),
    }


def ingest_mcf() -> list[dict]:
    pages = sorted(
        (p for p in RAW.glob("mcf_p*.json") if re.fullmatch(r"mcf_p\d+\.json", p.name)),
        key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)),
    )
    seen: set[str] = set()
    rows: list[dict] = []
    for path in pages:
        data = load_json(path)
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            continue
        for job in results:
            row = normalize_mcf_job(job)
            if not row:
                continue
            key = canon_url(row["url"])
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(row)
    write_jsonl(MCF_OUT, rows)
    print(f"mycareersfuture.jsonl pages={len(pages)} written={len(rows)}", flush=True)
    return rows


# ---- Jobsuche ----
def js_hits(payload) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    for key in ("ergebnisliste", "stellenangebote", "jobs"):
        val = payload.get(key)
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
    return []


def js_first_loc(hit: dict) -> dict:
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


def js_pretty_region(raw) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    key = s.upper().replace(" ", "_").replace("-", "_")
    if key in JS_REGION_MAP and key != "DEUTSCHLAND":
        return JS_REGION_MAP[key]
    if s.lower() in {"deutschland", "germany", "de"}:
        return ""
    return s.replace("_", "-").title() if s.isupper() else s


def js_posted(hit: dict) -> str:
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


def js_remote(hit: dict, title: str, desc: str) -> bool:
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
    return bool(JS_REMOTE_RE.search(f"{title} {desc}"))


def js_url(hit: dict, ref: str) -> str:
    for key in ("jobboerseUrl", "detailUrl", "url", "stellenangebotsUrl"):
        val = hit.get(key)
        if isinstance(val, str) and "arbeitsagentur.de" in val.lower():
            return val.strip()
    if ref:
        return f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}"
    return ""


def js_snippet(parts: list[str], n: int = 300) -> str:
    text = " — ".join(p.strip() for p in parts if p and str(p).strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


def normalize_js_hit(hit: dict) -> dict | None:
    ref = str(hit.get("referenznummer") or hit.get("refnr") or "").strip()
    hid = str(hit.get("hashId") or "").strip()
    ident = ref or hid
    if not ident:
        return None
    title = str(
        hit.get("stellenangebotsTitel") or hit.get("titel") or hit.get("beruf") or ""
    ).strip()
    company = str(hit.get("firma") or hit.get("arbeitgeber") or "").strip()
    loc = js_first_loc(hit)
    city = str(loc.get("ort") or loc.get("city") or "").strip()
    state = js_pretty_region(loc.get("region") or loc.get("bundesland") or "")
    posted = js_posted(hit)
    url = js_url(hit, ref or hid)
    if not url:
        return None
    desc = js_snippet(
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
    return {
        "id": f"jobsuche:{ident}",
        "title": title,
        "company": company,
        "country": "Germany",
        "state": state,
        "city": city,
        "remote": js_remote(hit, title, desc),
        "url": url,
        "posted_at": posted,
        "source": "jobsuche",
        "description": desc,
    }


def ingest_jobsuche() -> list[dict]:
    pages = sorted(
        (p for p in RAW.glob("jobsuche_p*.json") if re.fullmatch(r"jobsuche_p\d+\.json", p.name)),
        key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)),
    )
    seen: set[str] = set()
    rows: list[dict] = []
    for path in pages:
        payload = load_json(path)
        for hit in js_hits(payload):
            row = normalize_js_hit(hit)
            if not row:
                continue
            key = canon_url(row["url"])
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(row)
    write_jsonl(JS_OUT, rows)
    print(f"jobsuche.jsonl pages={len(pages)} written={len(rows)}", flush=True)
    return rows


# ---- Himalayas India merge ----
def him_url(j: dict) -> str:
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


def him_id(j: dict, url: str) -> str:
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
    guid = (j.get("guid") or "").strip()
    if guid:
        return f"himalayas:{guid.rstrip('/').split('/')[-1]}"
    return f"himalayas:{re.sub(r'[^a-z0-9]+', '-', (j.get('title') or 'job').lower()).strip('-')}"


def him_company(j: dict) -> str:
    name = (j.get("companyName") or "").strip()
    if name.lower() in {"name", "company", "n/a", "null", ""}:
        return (j.get("companySlug") or "").strip()
    return name


def him_posted(pub) -> str:
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


def merge_himalayas_india(city_canon: dict[str, str], country_folds: set[str]) -> tuple[int, int]:
    """Append new India-search jobs into himalayas.jsonl. Returns (pages, added)."""
    pages = sorted(
        (p for p in RAW.glob("himalayas_in_p*.json") if re.fullmatch(r"himalayas_in_p\d+\.json", p.name)),
        key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)),
    )
    existing: list[dict] = []
    seen: set[str] = set()
    if HIMALAYAS_PATH.exists():
        with HIMALAYAS_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                key = canon_url(str(obj.get("url") or ""))
                if not key or key in seen:
                    continue
                seen.add(key)
                existing.append(project(obj))

    added_rows: list[dict] = []
    for path in pages:
        data = load_json(path)
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list):
            continue
        for j in jobs:
            if not isinstance(j, dict):
                continue
            url = him_url(j)
            if not url:
                continue
            key = canon_url(url)
            if not key or key in seen:
                continue
            title = strip_html(j.get("title") or "")
            if not title:
                continue
            locs = j.get("locationRestrictions") or []
            if isinstance(locs, str):
                locs = [locs]
            city = ""
            for loc in locs:
                fl = fold_text(loc)
                if not fl or fl in country_folds:
                    continue
                if fl in city_canon:
                    city = city_canon[fl]
                    break
                if not city:
                    city = str(loc).strip()
            row = {
                "id": him_id(j, url),
                "title": title,
                "company": him_company(j),
                "country": "India",
                "state": "",
                "city": city,
                "remote": True,
                "url": url,
                "posted_at": him_posted(j.get("pubDate")),
                "source": "himalayas",
                "description": short_desc(j.get("excerpt") or j.get("description") or "", 400),
            }
            seen.add(key)
            added_rows.append(row)

    if added_rows:
        existing.extend(added_rows)
        write_jsonl(HIMALAYAS_PATH, existing)
    print(
        f"himalayas.jsonl pages={len(pages)} added={len(added_rows)} total={len(existing)}",
        flush=True,
    )
    return len(pages), len(added_rows)


# ---- state infer ----
def load_state_infer() -> tuple[dict, dict[tuple[str, str], str], dict[str, list[tuple[str, str]]], set[str], dict[str, str]]:
    table = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    country_aliases = table.get("country_aliases") or {}
    city_aliases = table.get("city_aliases") or {}
    lookup_rows = table.get("lookup") or []
    print(f"state-infer.json lookup_rows={len(lookup_rows)}", flush=True)

    alias_fold: dict[str, str] = {}
    for src, dest in country_aliases.items():
        alias_fold[fold_text(src)] = dest
        alias_fold[fold_text(dest)] = dest
    for c in ALLOWED:
        alias_fold[fold_text(c)] = c

    city_alias_fold: dict[str, str] = {}
    for src, dest in city_aliases.items():
        city_alias_fold[fold_text(src)] = dest

    exact: dict[tuple[str, str], str] = {}
    by_country: dict[str, list[tuple[str, str]]] = {c: [] for c in ALLOWED}
    city_canon: dict[str, str] = {}
    for row in lookup_rows:
        country = row.get("country") or ""
        city = row.get("city") or ""
        state = row.get("state") or ""
        if country not in ALLOWED or not city:
            continue
        folded = fold_text(city)
        if not folded:
            continue
        exact[(country, folded)] = state
        by_country.setdefault(country, []).append((folded, state))
        city_canon.setdefault(folded, city)
        alias_dest = city_alias_fold.get(folded)
        if alias_dest:
            city_canon.setdefault(fold_text(alias_dest), alias_dest)

    for src, dest in city_aliases.items():
        city_canon.setdefault(fold_text(src), dest)
        city_canon.setdefault(fold_text(dest), dest)

    for country, items in by_country.items():
        # longest city token first
        items.sort(key=lambda x: len(x[0]), reverse=True)
        # unique folded cities, first (longest) wins
        seen = set()
        uniq = []
        for folded, state in items:
            if folded in seen:
                continue
            seen.add(folded)
            uniq.append((folded, state))
        by_country[country] = uniq

    country_folds = set(alias_fold.keys())
    return alias_fold, exact, by_country, country_folds, city_canon


def resolve_country(raw: str, alias_fold: dict[str, str]) -> str:
    return alias_fold.get(fold_text(raw), "")


def infer_state(country: str, city: str, exact: dict, by_country: dict, city_alias_fold: dict[str, str]) -> str:
    if country not in ALLOWED or country == "Singapore":
        return ""
    raw_city = (city or "").strip()
    if not raw_city:
        return ""
    folded = fold_text(raw_city)
    if not folded:
        return ""
    # apply city alias on the full field
    aliased = city_alias_fold.get(folded)
    if aliased:
        folded_alias = fold_text(aliased)
        hit = exact.get((country, folded_alias))
        if hit:
            return hit
        hit = exact.get((country, folded))
        if hit:
            return hit
    hit = exact.get((country, folded))
    if hit:
        return hit
    # phrase / token match, longest known city wins
    for token, state in by_country.get(country, []):
        if not token:
            continue
        if re.search(r"\b" + re.escape(token) + r"\b", folded):
            return state
        # also try alias of token
        # (tokens already include alias rows from lookup)
    return ""


def apply_infer(jobs: list[dict], alias_fold, exact, by_country, city_alias_fold) -> tuple[int, int, int]:
    before = sum(1 for j in jobs if not (j.get("state") or "").strip())
    filled = 0
    cleared_de = 0
    for j in jobs:
        country_raw = j.get("country") or ""
        country = resolve_country(country_raw, alias_fold) or (country_raw if country_raw in ALLOWED else "")
        state = (j.get("state") or "").strip()
        city = j.get("city") or ""
        if state and not (country == "Germany" and state == "Delaware"):
            continue
        if country == "Germany" and state == "Delaware":
            j["state"] = ""
            state = ""
            cleared_de += 1
        inferred = infer_state(country, city, exact, by_country, city_alias_fold)
        if inferred:
            j["state"] = inferred
            filled += 1
        elif country == "Germany" and state == "":
            j["state"] = ""
    after = sum(1 for j in jobs if not (j.get("state") or "").strip())
    return before, after, filled, cleared_de


def load_all_jsonl() -> list[dict]:
    files = sorted(
        p
        for p in NORM.glob("*.jsonl")
        if p.is_file() and p.name != "all.jsonl"
    )
    # Supersede poorly-parsed mcf.jsonl when mycareersfuture.jsonl exists
    if MCF_OUT.exists():
        files = [p for p in files if p.name != "mcf.jsonl"]
    seen: set[str] = set()
    jobs: list[dict] = []
    per_file = {}
    for path in files:
        stats = {"read": 0, "kept": 0, "dups": 0}
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                stats["read"] += 1
                row = project(obj)
                key = canon_url(row["url"])
                if not key:
                    continue
                if key in seen:
                    stats["dups"] += 1
                    continue
                seen.add(key)
                jobs.append(row)
                stats["kept"] += 1
        per_file[path.name] = stats
    print("loaded_files", json.dumps(per_file, ensure_ascii=False), flush=True)
    return jobs


def country_counts(jobs: list[dict]) -> dict[str, int]:
    raw = Counter(j["country"] for j in jobs)
    out: dict[str, int] = {}
    for name in COUNTRY_ORDER:
        if name in raw:
            out[name] = raw[name]
    extras = sorted(k for k in raw if k not in COUNTRY_ORDER and k != "")
    for name in extras:
        out[name] = raw[name]
    if "" in raw:
        out[""] = raw[""]
    return out


def main() -> int:
    table = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    city_aliases = table.get("city_aliases") or {}
    country_aliases = table.get("country_aliases") or {}
    alias_fold, exact, by_country, country_folds, city_canon = load_state_infer()
    city_alias_fold = {fold_text(k): v for k, v in city_aliases.items()}

    ingest_mcf()
    ingest_jobsuche()
    merge_himalayas_india(city_canon, country_folds)

    jobs = load_all_jsonl()
    before, after, filled, cleared_de = apply_infer(
        jobs, alias_fold, exact, by_country, city_alias_fold
    )

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    by_source = dict(sorted(Counter(j["source"] or "unknown" for j in jobs).items()))
    by_country = country_counts(jobs)
    remote_n = sum(1 for j in jobs if j["remote"])
    onsite_n = len(jobs) - remote_n
    summary = {
        "total": len(jobs),
        "by_source": by_source,
        "by_country": by_country,
        "by_remote": {"remote": remote_n, "onsite": onsite_n},
        "updated_at": now,
    }
    write_jsonl(COMBINED, jobs)
    write_jsonl(ALL_PATH, jobs)
    write_json(SUMMARY, summary)

    print("==== RESULT ====", flush=True)
    print(f"total: {summary['total']}", flush=True)
    print("by_country:", json.dumps(by_country, ensure_ascii=False), flush=True)
    print("by_source:", json.dumps(by_source, ensure_ascii=False), flush=True)
    print(f"empty_state before: {before}", flush=True)
    print(f"empty_state after: {after}", flush=True)
    print(f"filled: {filled} cleared_germany_delaware: {cleared_de}", flush=True)
    print("by_remote:", json.dumps(summary["by_remote"], ensure_ascii=False), flush=True)
    print(f"updated_at: {now}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

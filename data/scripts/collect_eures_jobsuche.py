#!/usr/bin/env python3
"""Collect EURES + BA Jobsuche public APIs. Time-boxed. No invented jobs."""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")
DEBUG = Path("/workspace/jobs/debug")
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
TIMEBOX_SEC = 12 * 60
SLEEP_SEC = 0.30
PAGE_SIZE = 25

EURES_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
JOBSUCHE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"

COUNTRY = {
    "nl": "Netherlands",
    "fr": "France",
    "ie": "Ireland",
    "de": "Germany",
}

EURES_REMOTE_RE = re.compile(r"telework|home\s*office|remote", re.I)
JOBSUCHE_REMOTE_RE = re.compile(
    r"\bho\b|homeofficemoeglich|homeoffice|home[\s-]?office|heim[\s-]?telearbeit|telearbeit|heimarbeit|\bremote\b",
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
    print(f"{now_iso()} {msg}", flush=True)


def remaining(deadline: float) -> float:
    return deadline - time.time()


def write_error(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_debug(name: str, text: str) -> None:
    DEBUG.mkdir(parents=True, exist_ok=True)
    p = DEBUG / name
    prev = p.read_text(encoding="utf-8") if p.exists() else ""
    p.write_text(prev.rstrip() + "\n\n--- retry ---\n" + text, encoding="utf-8")


def http(method: str, url: str, headers: dict[str, str], data: bytes | None = None) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status, resp.read(), ""
    except urllib.error.HTTPError as e:
        body = e.read() if e.fp else b""
        return e.code, body, ""
    except Exception as e:
        return 0, b"", f"{type(e).__name__}: {e}"


def request_with_retry(method: str, url: str, headers: dict[str, str], data: bytes | None = None) -> tuple[int, bytes, str]:
    status, body, err = http(method, url, headers, data)
    if status == 429:
        time.sleep(1.0)
        status, body, err = http(method, url, headers, data)
    return status, body, err


def snippet(body: bytes, n: int = 500) -> str:
    return body[:n].decode("utf-8", "replace")


def parse_ms(value: object) -> str:
    if value is None or value == "":
        return ""
    try:
        n = int(value)
        if n > 10**12:
            n //= 1000
        if n < 10**8:
            return ""
        return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return str(value)


def eures_city(location_map: object, cc: str) -> str:
    if not isinstance(location_map, dict):
        return ""
    vals = location_map.get(cc.upper()) or location_map.get(cc) or []
    if isinstance(vals, list):
        for v in vals:
            if v:
                if isinstance(v, dict):
                    return str(v.get("city") or v.get("name") or v.get("region") or "").strip()
                return str(v).strip()
    for key, vals in location_map.items():
        if isinstance(vals, list):
            for v in vals:
                if v:
                    if isinstance(v, dict):
                        return str(v.get("city") or v.get("name") or "").strip()
                    s = str(v).strip()
                    if s and s.lower() not in {"null", "none"}:
                        return s
    return ""


def eures_remote(title: str, description: str) -> bool:
    return bool(EURES_REMOTE_RE.search(f"{title} {description}"))


def jobsuche_remote(*parts: object) -> bool:
    blobs = []
    for p in parts:
        if p is None:
            continue
        if isinstance(p, (list, tuple, dict)):
            blobs.append(json.dumps(p, ensure_ascii=False))
        else:
            blobs.append(str(p))
    return bool(JOBSUCHE_REMOTE_RE.search(" ".join(blobs)))


def normalize_eures(job: dict, cc: str) -> dict | None:
    jid = job.get("id")
    title = strip_html(job.get("title") or "")
    if not jid or not title:
        return None
    emp = job.get("employer") or {}
    company = ""
    if isinstance(emp, dict):
        company = strip_html(emp.get("name") or "")
    desc = job.get("description") or ""
    trans = job.get("translations") or {}
    if isinstance(trans, dict):
        for lang in ("en", "nl", "fr", "de", "ie"):
            block = trans.get(lang) or {}
            if isinstance(block, dict) and block.get("description"):
                desc = block.get("description") or desc
                break
    city = eures_city(job.get("locationMap"), cc)
    url = f"https://europa.eu/eures/portal/jv-se/jv-details/{urllib.parse.quote(str(jid), safe='')}"
    return {
        "id": f"eures:{jid}",
        "title": title,
        "company": company,
        "country": COUNTRY[cc],
        "state": "",
        "city": city,
        "remote": eures_remote(title, strip_html(desc)),
        "url": url,
        "posted_at": parse_ms(job.get("creationDate") or job.get("lastModificationDate")),
        "source": "eures",
        "description": short_desc(desc),
    }


def normalize_jobsuche(job: dict) -> dict | None:
    ref = job.get("referenznummer") or job.get("refnr") or job.get("hashId")
    title = strip_html(
        job.get("stellenangebotsTitel") or job.get("titel") or job.get("beruf") or ""
    )
    if not ref or not title:
        return None
    locs = job.get("stellenlokationen") or []
    city = state = ""
    if isinstance(locs, list) and locs:
        addr = (locs[0] or {}).get("adresse") if isinstance(locs[0], dict) else {}
        if isinstance(addr, dict):
            city = str(addr.get("ort") or "").strip()
            state = str(addr.get("region") or "").strip()
            if state:
                state = state.title()
    ao = job.get("arbeitsort") or {}
    if isinstance(ao, dict):
        city = city or str(ao.get("ort") or "").strip()
        state = state or str(ao.get("region") or "").strip()
    firma = job.get("firma") or job.get("arbeitgeber") or ""
    if isinstance(firma, dict):
        firma = firma.get("name") or ""
    posted = (
        job.get("datumErsteVeroeffentlichung")
        or (job.get("veroeffentlichungszeitraum") or {}).get("von")
        if isinstance(job.get("veroeffentlichungszeitraum"), dict)
        else job.get("datumErsteVeroeffentlichung")
        or job.get("aktuelleVeroeffentlichungsdatum")
        or ""
    )
    if isinstance(posted, dict):
        posted = posted.get("von") or ""
    url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{urllib.parse.quote(str(ref), safe='')}"
    remote = jobsuche_remote(
        title,
        job.get("hauptberuf"),
        job.get("alleBerufe"),
        job.get("homeoffice"),
        job.get("homeofficemoeglich"),
        job.get("arbeitszeit"),
        job.get("arbeitszeitmodelle"),
        json.dumps(job, ensure_ascii=False) if any(
            k in job for k in ("homeoffice", "homeofficemoeglich", "ho")
        ) else title,
    )
    # also scan stringified known remote-ish fields only — do not invent
    extra = " ".join(
        str(job.get(k) or "")
        for k in (
            "homeoffice",
            "homeofficemoeglich",
            "arbeitszeit",
            "stellenangebotsTitel",
            "hauptberuf",
        )
    )
    remote = remote or jobsuche_remote(extra)
    return {
        "id": f"jobsuche:{ref}",
        "title": title,
        "company": strip_html(firma),
        "country": "Germany",
        "state": state,
        "city": city,
        "remote": bool(remote),
        "url": url,
        "posted_at": str(posted or ""),
        "source": "jobsuche",
        "description": short_desc(job.get("stellenbeschreibung") or job.get("hauptberuf") or title),
    }


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    keys = ["id", "title", "company", "country", "state", "city", "remote", "url", "posted_at", "source", "description"]
    with tmp.open("w", encoding="utf-8") as fh:
        seen = set()
        for r in rows:
            if not r or not r.get("id") or r["id"] in seen:
                continue
            seen.add(r["id"])
            fh.write(json.dumps({k: r.get(k) for k in keys}, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp.replace(path)


def collect_eures(deadline: float) -> tuple[list[dict], dict]:
    stats = {
        "ok_pages": 0,
        "jobs": 0,
        "errors": [],
        "per_country": {},
        "probe": [],
    }
    rows: list[dict] = []
    headers = {
        "Content-Type": "application/json",
        "User-Agent": UA,
        "Accept": "application/json",
    }
    # Probe variants (print status + first 500)
    variants = [
        {"locationCodes": ["nl"], "publicationPeriod": "LAST_WEEK", "page": 1, "resultsPerPage": 25},
        {"locationCodes": ["nl"], "publicationPeriod": "LAST_WEEK"},
    ]
    working = None
    for i, payload in enumerate(variants, 1):
        if remaining(deadline) < 5:
            break
        body = json.dumps(payload).encode()
        status, raw, err = request_with_retry("POST", EURES_URL, headers, body)
        snip = snippet(raw) if raw else err
        print(f"EURES PROBE{i} status={status} body500={snip[:500]}", flush=True)
        stats["probe"].append({"payload": payload, "status": status, "snippet": snip[:500]})
        dbg = (
            f"URL: {EURES_URL}\nMETHOD: POST\nHEADERS:\n"
            f"  Content-Type: application/json\n  User-Agent: {UA}\n  Accept: application/json\n"
            f"BODY: {json.dumps(payload)}\nSTATUS: {status}\n"
            f"BODY_SNIPPET: {snip[:500]}\n"
        )
        if status in (401, 403):
            headers2 = dict(headers)
            headers2["Origin"] = "https://europa.eu"
            time.sleep(SLEEP_SEC)
            status2, raw2, err2 = request_with_retry("POST", EURES_URL, headers2, body)
            snip2 = snippet(raw2) if raw2 else err2
            print(f"EURES PROBE{i}+Origin status={status2} body500={snip2[:500]}", flush=True)
            write_debug("eures.txt", dbg + f"\nRETRY Origin status={status2}\nBODY_SNIPPET: {snip2[:500]}\n")
            if status2 == 200:
                working = payload
                headers = headers2
                raw = raw2
                status = status2
        else:
            write_debug("eures.txt", dbg)
        if status == 200:
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                data = None
            if isinstance(data, dict) and (data.get("jvs") or data.get("numberRecords") is not None):
                working = payload
                # save probe page if it has jobs
                if data.get("jvs"):
                    write_json(RAW / "eures_nl_p1.json", data)
                    stats["ok_pages"] += 1
                    for j in data.get("jvs") or []:
                        rec = normalize_eures(j, "nl")
                        if rec:
                            rows.append(rec)
                    stats["jobs"] = len(rows)
                    stats["per_country"]["nl"] = {"pages": 1, "jobs": len(rows), "numberRecords": data.get("numberRecords")}
                break
        time.sleep(SLEEP_SEC)

    if working is None:
        last = stats["probe"][-1] if stats["probe"] else {}
        write_error(
            RAW / "eures.error.txt",
            f"status={last.get('status')}\n{last.get('snippet','no successful probe')}\n",
        )
        log("EURES failed all probes")
        return rows, stats

    # Paginate remaining countries. NL page 1 already saved if working payload used page 1.
    start_page = {"nl": 2} if stats["per_country"].get("nl") else {"nl": 1}
    for cc in ("nl", "fr", "ie", "de"):
        if remaining(deadline) < 8:
            log(f"EURES timebox stop before {cc}")
            break
        pages = stats["per_country"].get(cc, {}).get("pages", 0)
        jobs_cc = stats["per_country"].get(cc, {}).get("jobs", 0)
        page = start_page.get(cc, 1)
        number_records = None
        empty_streak = 0
        while remaining(deadline) >= 8:
            payload = {
                "locationCodes": [cc],
                "publicationPeriod": "LAST_WEEK",
                "page": page,
                "resultsPerPage": PAGE_SIZE,
            }
            body = json.dumps(payload).encode()
            status, raw, err = request_with_retry("POST", EURES_URL, headers, body)
            if status != 200:
                snip = snippet(raw) if raw else err
                stats["errors"].append({"cc": cc, "page": page, "status": status, "snippet": snip[:300]})
                log(f"EURES {cc} p{page} status={status}")
                if status in (401, 403, 0) and page == start_page.get(cc, 1):
                    write_error(RAW / "eures.error.txt", f"status={status}\n{snip[:500]}\n")
                if status >= 500 or status == 0:
                    time.sleep(1.0)
                    empty_streak += 1
                    if empty_streak >= 3:
                        break
                    page += 1
                    time.sleep(SLEEP_SEC)
                    continue
                break
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception as e:
                stats["errors"].append({"cc": cc, "page": page, "status": status, "snippet": f"JSON {e}"})
                break
            jvs = data.get("jvs") or []
            number_records = data.get("numberRecords", number_records)
            if not jvs:
                log(f"EURES {cc} p{page} empty jvs numberRecords={number_records}")
                break
            write_json(RAW / f"eures_{cc}_p{page}.json", data)
            n_before = len(rows)
            for j in jvs:
                rec = normalize_eures(j, cc)
                if rec:
                    rows.append(rec)
            added = len(rows) - n_before
            pages += 1
            jobs_cc += added
            stats["ok_pages"] += 1
            stats["jobs"] = len(rows)
            log(f"EURES {cc} p{page} status=200 jvs={len(jvs)} added={added} total={len(rows)} numberRecords={number_records}")
            if len(jvs) < PAGE_SIZE:
                break
            if number_records is not None and page * PAGE_SIZE >= int(number_records):
                break
            page += 1
            time.sleep(SLEEP_SEC)
        stats["per_country"][cc] = {"pages": pages, "jobs": jobs_cc, "numberRecords": number_records}
        time.sleep(SLEEP_SEC)
    return rows, stats


def collect_jobsuche(deadline: float) -> tuple[list[dict], dict]:
    stats = {"ok_pages": 0, "jobs": 0, "errors": [], "queries": [], "probe": []}
    rows: list[dict] = []
    headers = {
        "X-API-Key": "jobboerse-jobsuche",
        "User-Agent": UA,
        "Accept": "application/json",
    }

    def get(qs: str) -> tuple[int, bytes, str, str]:
        url = JOBSUCHE_URL + "?" + qs
        status, raw, err = request_with_retry("GET", url, headers)
        return status, raw, err, url

    # Probe size=1 first
    probe_qs = "size=1&page=1&arbeitszeit=ho&veroeffentlichtseit=14"
    status, raw, err, url = get(probe_qs)
    snip = snippet(raw) if raw else err
    print(f"JOBSUCHE PROBE ho status={status} body500={snip[:500]}", flush=True)
    stats["probe"].append({"qs": probe_qs, "status": status, "snippet": snip[:500]})
    write_debug(
        "jobsuche.txt",
        f"URL: {url}\nMETHOD: GET\nHEADERS:\n  X-API-Key: jobboerse-jobsuche\n  User-Agent: {UA}\n"
        f"  Accept: application/json\nSTATUS: {status}\nBODY_SNIPPET: {snip[:500]}\n",
    )
    ho_ok = False
    if status == 200:
        try:
            pdata = json.loads(raw.decode("utf-8"))
            ho_ok = bool(pdata.get("ergebnisliste") or pdata.get("stellenangebote")) and int(pdata.get("maxErgebnisse") or 0) > 0
        except Exception:
            ho_ok = False
    if not ho_ok:
        # fallback probes
        for qs in (
            "size=1&page=1&was=homeoffice&veroeffentlichtseit=14",
            "size=1&page=1&was=homeoffice",
            "size=1&page=1&veroeffentlichtseit=14",
        ):
            if remaining(deadline) < 5:
                break
            time.sleep(SLEEP_SEC)
            status, raw, err, url = get(qs)
            snip = snippet(raw) if raw else err
            print(f"JOBSUCHE PROBE {qs} status={status} body500={snip[:500]}", flush=True)
            stats["probe"].append({"qs": qs, "status": status, "snippet": snip[:500]})
            write_debug(
                "jobsuche.txt",
                f"URL: {url}\nMETHOD: GET\nHEADERS:\n  X-API-Key: jobboerse-jobsuche\n  User-Agent: {UA}\n"
                f"  Accept: application/json\nSTATUS: {status}\nBODY_SNIPPET: {snip[:500]}\n",
            )
            if status == 200:
                try:
                    pdata = json.loads(raw.decode("utf-8"))
                except Exception:
                    pdata = None
                if isinstance(pdata, dict) and (pdata.get("ergebnisliste") or pdata.get("stellenangebote")):
                    break

    queries = []
    if ho_ok:
        queries.append(("ho", "size={size}&page={page}&arbeitszeit=ho&veroeffentlichtseit=14"))
        queries.append(("de", "size={size}&page={page}&veroeffentlichtseit=14"))
    else:
        # remote-ish first via was=homeoffice, then broader DE
        queries.append(("ho", "size={size}&page={page}&was=homeoffice&veroeffentlichtseit=14"))
        queries.append(("de", "size={size}&page={page}&veroeffentlichtseit=14"))

    file_n = 0
    any_ok = False
    for qname, qtmpl in queries:
        if remaining(deadline) < 8:
            log(f"JOBSUCHE timebox stop before {qname}")
            break
        page = 1
        q_pages = 0
        q_jobs = 0
        while remaining(deadline) >= 8:
            qs = qtmpl.format(size=PAGE_SIZE, page=page)
            status, raw, err, url = get(qs)
            if status != 200:
                snip = snippet(raw) if raw else err
                stats["errors"].append({"query": qname, "page": page, "status": status, "snippet": snip[:300]})
                log(f"JOBSUCHE {qname} p{page} status={status}")
                if status in (401, 403, 0) and page == 1 and not any_ok:
                    write_error(RAW / "jobsuche.error.txt", f"status={status}\n{snip[:500]}\n")
                break
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception as e:
                stats["errors"].append({"query": qname, "page": page, "status": status, "snippet": f"JSON {e}"})
                break
            jobs = data.get("ergebnisliste") or data.get("stellenangebote") or []
            max_e = data.get("maxErgebnisse")
            if not jobs:
                log(f"JOBSUCHE {qname} p{page} empty maxErgebnisse={max_e}")
                break
            file_n += 1
            write_json(RAW / f"jobsuche_p{file_n}.json", data)
            n_before = len(rows)
            for j in jobs:
                rec = normalize_jobsuche(j)
                if rec:
                    # if this page came from homeoffice search, still only mark remote via fields/text
                    rows.append(rec)
            added = len(rows) - n_before
            q_pages += 1
            q_jobs += added
            stats["ok_pages"] += 1
            stats["jobs"] = len(rows)
            any_ok = True
            log(f"JOBSUCHE {qname} file=p{file_n} api_page={page} status=200 n={len(jobs)} added={added} total={len(rows)} max={max_e}")
            if len(jobs) < PAGE_SIZE:
                break
            try:
                if max_e is not None and page * PAGE_SIZE >= int(max_e):
                    break
            except Exception:
                pass
            page += 1
            time.sleep(SLEEP_SEC)
        stats["queries"].append({"name": qname, "pages": q_pages, "jobs": q_jobs})
        time.sleep(SLEEP_SEC)

    if not any_ok and not (RAW / "jobsuche.error.txt").exists():
        last = stats["probe"][-1] if stats["probe"] else {}
        write_error(
            RAW / "jobsuche.error.txt",
            f"status={last.get('status')}\n{last.get('snippet','no jobs')}\n",
        )
    return rows, stats


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    DEBUG.mkdir(parents=True, exist_ok=True)
    start = time.time()
    deadline = start + TIMEBOX_SEC
    # Split: EURES ~7.5 min, Jobsuche the rest (min 3.5 min reserved)
    eures_deadline = start + 7.5 * 60
    # If we finish EURES early, Jobsuche gets leftover.

    log("START eures+jobsuche timebox=12m")
    eures_rows, eures_stats = collect_eures(min(deadline, eures_deadline))
    write_jsonl(NORM / "eures.jsonl", eures_rows)
    log(f"EURES wrote {len(eures_rows)} normalized jobs, pages={eures_stats['ok_pages']}")

    jobsuche_rows, js_stats = collect_jobsuche(deadline)
    write_jsonl(NORM / "jobsuche.jsonl", jobsuche_rows)
    log(f"JOBSUCHE wrote {len(jobsuche_rows)} normalized jobs, pages={js_stats['ok_pages']}")

    report = {
        "elapsed_sec": round(time.time() - start, 1),
        "eures": {
            "pages": eures_stats["ok_pages"],
            "jobs": len(eures_rows),
            "per_country": eures_stats["per_country"],
            "errors": eures_stats["errors"],
            "probe": eures_stats["probe"],
        },
        "jobsuche": {
            "pages": js_stats["ok_pages"],
            "jobs": len(jobsuche_rows),
            "queries": js_stats["queries"],
            "errors": js_stats["errors"],
            "probe": js_stats["probe"],
        },
    }
    (RAW / "_eures_jobsuche_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    log("DONE collect")
    return 0


if __name__ == "__main__":
    sys.exit(main())

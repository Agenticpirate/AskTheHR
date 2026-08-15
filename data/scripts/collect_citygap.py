#!/usr/bin/env python3
"""Fill HARD city-gap ATS boards. Public JSON only. Skip existing gh_/lever_ files."""
from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

import requests

RAW = Path("/workspace/jobs/raw")
LOG_PATH = RAW / "ats_citygap_log.txt"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
TIMEOUT = 2.0
DEADLINE = time.time() + 10 * 60
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "application/json"})

# Existing GH/Lever slugs to skip even if we list them
SKIP_EXISTING_SLUGS = {
    "adyen", "n26", "autotrader", "stripe", "intercom", "hubspot",
    "cultureamp", "doctolib", "dataiku", "mirakl", "qonto", "shifttechnology",
}

GH_TOKENS = [
    # NL
    "asml", "philips", "signify", "coolblue", "picnic", "takeaway", "tomtom",
    "mollie", "bunq", "messagebird", "backbase", "bookingcom", "booking-com",
    "transavia", "klm", "ing", "abnamro", "rabobank", "wehkamp",
    # FR
    "blablacar", "criteo", "contentsquare", "ledger", "alan", "spendesk",
    "swile", "backmarket", "deezer", "ovh", "ovhcloud", "vestiairecollective",
    "leboncoin", "manomano", "capgemini", "dassault", "airbus", "thales",
    "loreal", "stationf",
    # AU
    "afterpay", "employmenthero", "reagroup", "seek", "xero", "wisetechglobal",
    "envato", "campaignmonitor", "zipco", "tyro", "atlassian2", "atlassian",
    # IE
    "accenture", "workdaydublin",
    # UK regional
    "arm", "armholdings", "cambridge", "cambridgeconsultants", "darktrace",
    "darktrce", "ocado", "ocadogroup", "trainline", "rightmove", "bbc",
    "theguardian",
    # IN
    "flipkart", "swiggy", "zomato", "razorpay", "phonepe", "paytm",
    "freshworks", "zoho", "infogain", "mindtree", "infosys", "wipro", "tcs",
    # SG
    "grab", "shopee", "seagroup", "lazada", "carousell", "propertyguru",
    "endowus", "shopback", "ninjavan", "garena", "sea",
]

LEVER_SLUGS = [
    "asml", "philips", "grab", "xero", "envato", "afterpay", "seek",
]

JOBICY_GEOS = ["australia", "netherlands", "france", "singapore", "uk"]


def uniq_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = x.lower().strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def job_count(data: Any) -> int:
    if data is None:
        return 0
    if isinstance(data, list):
        return len(data)
    if not isinstance(data, dict):
        return 0
    for key in ("jobs", "postings", "results", "data", "jobPostings"):
        v = data.get(key)
        if isinstance(v, list):
            return len(v)
    return 0


def sleep_gap() -> None:
    time.sleep(random.uniform(0.150, 0.250))


def fetch(url: str) -> tuple[int, Any | None, str]:
    last_err = ""
    for attempt in range(2):
        if time.time() >= DEADLINE:
            return 0, None, "deadline"
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
        except requests.Timeout:
            return 0, None, "timeout"
        except requests.RequestException as e:
            return 0, None, type(e).__name__
        if r.status_code == 429:
            last_err = "429"
            if attempt == 0:
                time.sleep(1.0)
                continue
            return 429, None, "429"
        if r.status_code != 200:
            return r.status_code, None, ""
        try:
            return 200, r.json(), ""
        except ValueError:
            return r.status_code, None, "non-json"
    return 0, None, last_err or "fail"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []
    new_boards: list[tuple[str, str, int]] = []
    n404 = 0
    skipped_exist = 0
    other = 0
    written: list[str] = []

    def record(slug: str, ats: str, status: str, count: int) -> None:
        line = f"{slug}\t{ats}\t{status}\t{count}"
        log_lines.append(line)
        print(line, flush=True)

    # Greenhouse
    for token in uniq_keep_order(GH_TOKENS):
        if time.time() >= DEADLINE:
            record(token, "greenhouse", "skipped_deadline", 0)
            continue
        dest = RAW / f"gh_{token}.json"
        if dest.exists() or token in SKIP_EXISTING_SLUGS:
            skipped_exist += 1
            record(token, "greenhouse", "skip_exists", 0)
            continue
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        status, data, err = fetch(url)
        sleep_gap()
        if status == 200 and data is not None:
            n = job_count(data)
            if n > 0:
                dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                written.append(dest.name)
                new_boards.append((token, "greenhouse", n))
                record(token, "greenhouse", "200", n)
            else:
                record(token, "greenhouse", "200_empty", 0)
        elif status == 404:
            n404 += 1
            record(token, "greenhouse", "404", 0)
        elif err:
            other += 1
            record(token, "greenhouse", err, 0)
        else:
            other += 1
            record(token, "greenhouse", str(status), 0)

    # Lever
    for slug in uniq_keep_order(LEVER_SLUGS):
        if time.time() >= DEADLINE:
            record(slug, "lever", "skipped_deadline", 0)
            continue
        dest = RAW / f"lever_{slug}.json"
        if dest.exists() or slug in SKIP_EXISTING_SLUGS:
            skipped_exist += 1
            record(slug, "lever", "skip_exists", 0)
            continue
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        status, data, err = fetch(url)
        sleep_gap()
        if status == 200 and data is not None:
            n = job_count(data)
            if n > 0:
                dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                written.append(dest.name)
                new_boards.append((slug, "lever", n))
                record(slug, "lever", "200", n)
            else:
                record(slug, "lever", "200_empty", 0)
        elif status == 404:
            n404 += 1
            record(slug, "lever", "404", 0)
        elif err:
            other += 1
            record(slug, "lever", err, 0)
        else:
            other += 1
            record(slug, "lever", str(status), 0)

    # Jobicy geos — skip if file exists
    for geo in JOBICY_GEOS:
        if time.time() >= DEADLINE:
            record(geo, "jobicy", "skipped_deadline", 0)
            continue
        dest = RAW / f"jobicy_{geo}.json"
        if dest.exists():
            skipped_exist += 1
            record(geo, "jobicy", "skip_exists", 0)
            continue
        url = f"https://jobicy.com/api/v2/remote-jobs?count=100&geo={geo}"
        status, data, err = fetch(url)
        sleep_gap()
        if status == 200 and data is not None:
            n = job_count(data)
            if n > 0:
                dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                written.append(dest.name)
                new_boards.append((geo, "jobicy", n))
                record(geo, "jobicy", "200", n)
            else:
                record(geo, "jobicy", "200_empty", 0)
        elif status == 404:
            n404 += 1
            record(geo, "jobicy", "404", 0)
        elif err:
            other += 1
            record(geo, "jobicy", err, 0)
        else:
            other += 1
            record(geo, "jobicy", str(status), 0)

    summary = {
        "new_boards": [{"slug": s, "ats": a, "count": n} for s, a, n in new_boards],
        "new_board_count": len(new_boards),
        "files_written": written,
        "n404": n404,
        "skipped_exist": skipped_exist,
        "other_errors": other,
        "elapsed_sec": round(time.time() - (DEADLINE - 10 * 60), 1),
    }
    log_lines.append("")
    log_lines.append("==== SUMMARY ====")
    log_lines.append(json.dumps(summary, ensure_ascii=False, indent=2))
    LOG_PATH.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print("==== SUMMARY ====", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()

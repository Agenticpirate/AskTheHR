#!/usr/bin/env python3
"""Second-pass city-gap ATS: alt tokens + Himalayas q= city search. Skip existing files."""
from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

RAW = Path("/workspace/jobs/raw")
LOG_PATH = RAW / "ats_citygap_log.txt"
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
TIMEOUT = 2.0
DEADLINE = time.time() + 8 * 60
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "application/json"})

# Non-US / gap-region tokens (do NOT add US boards)
GH_TOKENS = [
    # confirmed from search
    "housinganywhere", "cambridgeconsultantslimited", "cambridgeconsultants",
    "thefork", "dept", "cityswift", "tide", "ocadotechnology",
    # listed-company alts
    "justeat", "justeattakeaway", "takeawaycom", "thuisbezorgd",
    "bird", "message-bird", "molliepayments", "backbasecom",
    "tomtominternational", "picnictechnologies", "coolbluebv", "bunqbank",
    "asmlholding", "asmlnv", "royalphilips", "philipsresearch", "signifynv",
    "booking", "transaviaairlines", "airfranceklm", "ingbank", "abn-amro",
    "wehkampnl", "comuto", "criteosa", "contentsquarehq", "ledgerhq",
    "alanhealth", "alanfr", "back-market", "backmarketfr",
    "vestiaire-collective", "leboncoinfr", "mano-mano", "station-f",
    "lorealparis", "employment-hero", "employmentherohq", "rea",
    "realestatecomau", "seeklimited", "xerolimited", "xeroanz", "wisetech",
    "wise-tech", "envatomarket", "campaign-monitor", "zip", "zipmoney",
    "zipau", "tyropayments", "afterpaytouch", "accentureireland",
    "armltd", "armcom", "darktraceai", "darktraceuk", "thetrainline",
    "trainlinecom", "rightmoveplc", "bbcstudios", "guardiannewsandmedia",
    "gnm", "guardian", "ocado", "ocadoretail", "razorpayhq",
    "freshworksinc", "freshdesk", "grabtaxi", "grabholdings", "grabsg",
    "sealimited", "seagroupsg", "shopeesg", "lazadasg", "carousellsg",
    "propertygurusg", "ninja-van", "ninjavalogistics", "garenasg",
    # more regional (non-US)
    "pennylane", "payfit", "aircall", "algolia", "dashlane", "livestorm",
    "huggingface", "mistral", "photoroom", "evaneos", "meero", "lydia",
    "shine", "klaxoon", "sendcloud", "mendix", "nxp", "nexperia",
    "exactsoftware", "visma", "bux", "deliveroo", "starlingbank",
    "checkoutcom", "revolut", "sophos", "featurespace", "raspberrypi",
    "jagex", "frontierdevelopments", "airwallex", "safetyculture",
    "deputy", "linktree", "lyra", "lyratechnology", "lyragroup",
    "flutter", "flutterentertainment", "iconplc", "chargebee", "postman",
    "browserstack", "innovaccer", "whatfix", "druva", "mindtickle",
    "sprinklr", "meesho", "cred", "groww", "infogain", "netsolutions",
    "quark", "ltimindtree", "persistent", "cashfree", "juspay",
    "fundingsocieties", "stashaway", "syfe", "foodpanda", "zalora",
    "99co", "razer", "carousell", "propertyguru", "endowus", "shopback",
    "ninjavan", "garena", "seagroup", "poolside", "dust", "recast",
    "passculture", "veepee", "cdiscount", "urbancompany", "delhivery",
    "sharechat", "dream11", "policybazaar", "nykaa", "myntra", "ola",
    "unacademy", "byjus", "payu", "cityswiftireland",
]

LEVER_SLUGS = [
    "housinganywhere", "thefork", "dept", "cityswift", "tide",
    "cambridgeconsultants", "mollie", "bunq", "alan", "criteo",
    "ledger", "grabtaxi", "pennylane", "payfit", "aircall", "algolia",
    "employmenthero", "airwallex", "razorpay", "chargebee", "postman",
    "browserstack", "carousell", "propertyguru", "endowus", "shopback",
    "ninjavan", "justeat", "deliveroo", "coolblue", "picnic", "tomtom",
    "backbase", "messagebird", "blablacar", "contentsquare", "spendesk",
    "swile", "backmarket", "deezer", "leboncoin", "manomano", "darktrace",
    "ocado", "trainline", "rightmove", "freshworks", "flipkart", "swiggy",
    "zomato", "phonepe", "grab", "shopee", "lazada", "garena", "sea",
    "xero", "envato", "afterpay", "seek", "asml", "philips",
]

# Himalayas city/q (works). Do not dump full countries.
HIMALAYA = [
    ("NL", "Rotterdam"), ("NL", "The Hague"), ("NL", "Den Haag"),
    ("NL", "Utrecht"), ("NL", "Eindhoven"),
    ("FR", "Lyon"), ("FR", "Toulouse"), ("FR", "Lille"), ("FR", "Marseille"),
    ("FR", "Nantes"), ("FR", "Rennes"), ("FR", "Strasbourg"),
    ("FR", "Grenoble"), ("FR", "Nice"), ("FR", "Montpellier"),
    ("AU", "Perth"),
    ("SG", "Singapore"),
    ("IE", "Galway"), ("IE", "Limerick"), ("IE", "remote"),
    ("IN", "New Delhi"), ("IN", "Chandigarh"), ("IN", "Mohali"),
    ("GB", "Cambridge"), ("GB", "Leeds"), ("GB", "Sheffield"), ("GB", "Bristol"),
    ("UK", "Cambridge"), ("UK", "Leeds"), ("UK", "Sheffield"), ("UK", "Bristol"),
]


def uniq(items):
    seen, out = set(), []
    for x in items:
        k = x.lower().strip()
        if k and k not in seen:
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


def sleep_gap():
    time.sleep(random.uniform(0.150, 0.250))


def fetch(url: str) -> tuple[int, Any | None, str]:
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
    return 0, None, "fail"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log_lines = ["", "==== PASS 2 ===="]
    new_boards = []
    n404 = 0
    skipped = 0
    other = 0
    written = []

    def record(slug, ats, status, count):
        line = f"{slug}\t{ats}\t{status}\t{count}"
        log_lines.append(line)
        print(line, flush=True)

    for token in uniq(GH_TOKENS):
        if time.time() >= DEADLINE:
            record(token, "greenhouse", "skipped_deadline", 0)
            continue
        dest = RAW / f"gh_{token}.json"
        if dest.exists():
            skipped += 1
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

    for slug in uniq(LEVER_SLUGS):
        if time.time() >= DEADLINE:
            record(slug, "lever", "skipped_deadline", 0)
            continue
        dest = RAW / f"lever_{slug}.json"
        if dest.exists():
            skipped += 1
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

    for country, q in HIMALAYA:
        if time.time() >= DEADLINE:
            record(f"{country}:{q}", "himalayas", "skipped_deadline", 0)
            continue
        slug = f"{country}_{q}".lower().replace(" ", "")
        dest = RAW / f"himalayas_q_{slug}.json"
        if dest.exists():
            skipped += 1
            record(slug, "himalayas", "skip_exists", 0)
            continue
        url = f"https://himalayas.app/jobs/api/search?country={quote(country)}&q={quote(q)}&sort=recent&page=1"
        status, data, err = fetch(url)
        sleep_gap()
        if status == 200 and data is not None:
            n = job_count(data)
            if n > 0:
                dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                written.append(dest.name)
                new_boards.append((slug, "himalayas", n))
                record(slug, "himalayas", "200", n)
            else:
                record(slug, "himalayas", "200_empty", 0)
        elif status == 404:
            n404 += 1
            record(slug, "himalayas", "404", 0)
        elif err:
            other += 1
            record(slug, "himalayas", err, 0)
        else:
            other += 1
            record(slug, "himalayas", str(status), 0)

    summary = {
        "pass": 2,
        "new_boards": [{"slug": s, "ats": a, "count": n} for s, a, n in new_boards],
        "new_board_count": len(new_boards),
        "files_written": written,
        "n404": n404,
        "skipped_exist": skipped,
        "other_errors": other,
    }
    log_lines.append("")
    log_lines.append("==== PASS 2 SUMMARY ====")
    log_lines.append(json.dumps(summary, ensure_ascii=False, indent=2))
    prev = LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else ""
    LOG_PATH.write_text(prev.rstrip() + "\n" + "\n".join(log_lines) + "\n", encoding="utf-8")
    print("==== PASS 2 SUMMARY ====", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()

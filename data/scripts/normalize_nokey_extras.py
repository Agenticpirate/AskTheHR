#!/usr/bin/env python3
"""Normalize RFJ, Working Nomads, and RemoteJobs.org raw dumps."""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

RAW = Path("/workspace/jobs/raw")
OUT = Path("/workspace/jobs/normalized")

TARGET = [
    "USA", "India", "Canada", "UK", "Australia",
    "Germany", "Netherlands", "Ireland", "Singapore", "France",
]
TARGET_SET = set(TARGET)

ALIASES = {
    "usa": "USA", "us": "USA", "u.s": "USA", "u.s.a": "USA",
    "united states": "USA", "united states of america": "USA", "america": "USA",
    "india": "India", "bharat": "India",
    "canada": "Canada",
    "uk": "UK", "u.k": "UK", "united kingdom": "UK", "great britain": "UK",
    "britain": "UK", "england": "UK", "scotland": "UK", "wales": "UK",
    "northern ireland": "UK", "gb": "UK",
    "australia": "Australia",
    "germany": "Germany", "deutschland": "Germany",
    "netherlands": "Netherlands", "the netherlands": "Netherlands", "holland": "Netherlands",
    "ireland": "Ireland", "republic of ireland": "Ireland", "eire": "Ireland",
    "singapore": "Singapore",
    "france": "France",
}

US_STATES = {
    "alabama": "Alabama", "alaska": "Alaska", "arizona": "Arizona", "arkansas": "Arkansas",
    "california": "California", "colorado": "Colorado", "connecticut": "Connecticut",
    "delaware": "Delaware", "florida": "Florida", "georgia": "Georgia", "hawaii": "Hawaii",
    "idaho": "Idaho", "illinois": "Illinois", "indiana": "Indiana", "iowa": "Iowa",
    "kansas": "Kansas", "kentucky": "Kentucky", "louisiana": "Louisiana", "maine": "Maine",
    "maryland": "Maryland", "massachusetts": "Massachusetts", "michigan": "Michigan",
    "minnesota": "Minnesota", "mississippi": "Mississippi", "missouri": "Missouri",
    "montana": "Montana", "nebraska": "Nebraska", "nevada": "Nevada",
    "new hampshire": "New Hampshire", "new jersey": "New Jersey", "new mexico": "New Mexico",
    "new york": "New York", "north carolina": "North Carolina", "north dakota": "North Dakota",
    "ohio": "Ohio", "oklahoma": "Oklahoma", "oregon": "Oregon", "pennsylvania": "Pennsylvania",
    "rhode island": "Rhode Island", "south carolina": "South Carolina",
    "south dakota": "South Dakota", "tennessee": "Tennessee", "texas": "Texas",
    "utah": "Utah", "vermont": "Vermont", "virginia": "Virginia", "washington": "Washington",
    "west virginia": "West Virginia", "wisconsin": "Wisconsin", "wyoming": "Wyoming",
    "district of columbia": "District of Columbia",
}

WORLDWIDE_EXACT = {
    "worldwide", "anywhere", "anywhere in the world", "global", "remote",
    "remote job", "work from home", "wfh", "fully remote", "100% remote",
    "international", "remote worldwide", "distributed", "unrestricted",
    "work from anywhere",
}

MULTI_REGION = {
    "europe", "emea", "apac", "latam", "latin america", "north america",
    "south america", "americas", "asia", "africa", "middle east", "eu",
}

# Specific non-target countries: drop if these are the only geo signal
OTHER_COUNTRY = {
    "philippines", "bulgaria", "mexico", "argentina", "vietnam", "poland",
    "switzerland", "romania", "taiwan", "egypt", "south africa", "japan",
    "spain", "brazil", "colombia", "chile", "peru", "portugal", "italy",
    "sweden", "norway", "denmark", "finland", "belgium", "austria",
    "czech republic", "czechia", "hungary", "greece", "turkey", "israel",
    "uae", "united arab emirates", "nigeria", "kenya", "pakistan",
    "bangladesh", "indonesia", "malaysia", "thailand", "south korea",
    "korea", "china", "russia", "ukraine", "new zealand",
}


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def strip_html(text):
    if not text:
        return ""
    text = html.unescape(str(text))
    try:
        s = HTMLStripper()
        s.feed(text)
        text = s.get_text()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def short_desc(text, limit=300):
    t = strip_html(text)
    return t if len(t) <= limit else t[:limit].rstrip()


def clean_token(token):
    t = (token or "").strip()
    t = re.sub(r"[\U0001F1E0-\U0001F1FF]", "", t)
    t = re.sub(r"\s+", " ", t).strip(" \t.,;:-")
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    return t


def norm_country(token):
    t = clean_token(token).lower().replace(".", "")
    t = re.sub(r"\s+", " ", t).strip()
    return ALIASES.get(t)


def is_worldwide(token):
    t = clean_token(token).lower()
    if not t:
        return True
    if t in WORLDWIDE_EXACT:
        return True
    if "anywhere" in t or "worldwide" in t or "work from home" in t:
        return True
    if t == "global" or t.startswith("global"):
        return True
    # timezone windows are eligibility, not a country
    if "timezone" in t or "time zone" in t or re.search(r"\b(cet|cst|est|pst|gmt|utc)\b", t):
        return True
    if re.search(r"[+\-]\s*/?\s*\d+\s*hours?", t):
        return True
    return False


def is_multi_region(token):
    t = clean_token(token).lower()
    if t in MULTI_REGION:
        return True
    # "Europe, North America, Latin America, APAC"
    parts = [p.strip() for p in re.split(r"[,;/|]+", t) if p.strip()]
    if len(parts) >= 2 and all(
        p in MULTI_REGION or p in WORLDWIDE_EXACT or is_worldwide(p) or norm_country(p)
        for p in parts
    ):
        return True
    return False


def is_other_country(token):
    t = clean_token(token).lower().replace(".", "")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(remote|hybrid)\s*[-,:]?\s*", "", t).strip()
    return t in OTHER_COUNTRY


def parse_posted_at(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        n = int(value)
        if n > 10**12:
            n //= 1000
        try:
            return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if "T" in s or " " in s:
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return s


def _split_loc_bits(text):
    t = re.sub(r"\b(and|or|only)\b", ",", str(text), flags=re.I)
    t = t.replace(";", ",").replace("|", ",")
    bits = []
    for part in re.split(r"[,/]+", t):
        part = part.strip()
        if not part:
            continue
        # "Japan - Remote" / "Remote - Colombia" / "Remote: US"
        part = re.sub(r"^(remote|hybrid|us remote|u\.s\.? remote)\s*[-,:]\s*", "", part, flags=re.I)
        part = re.sub(r"\s*[-,:]\s*(remote|hybrid)$", "", part, flags=re.I)
        part = part.strip(" -,:;")
        if part:
            bits.append(part)
    return bits


def parse_locs(parts):
    """Return (country, state, city, keep). keep=False if only non-target country."""
    tokens = []
    for p in parts:
        if p is None:
            continue
        if isinstance(p, (list, tuple)):
            tokens.extend(str(x) for x in p if x)
        else:
            s = str(p).strip()
            if s:
                tokens.append(s)
    if not tokens:
        return "", "", "", True

    found = []
    state = ""
    city = ""
    worldwide = False
    multi = False
    other_only_hits = 0

    expanded = []
    for t in tokens:
        expanded.extend(_split_loc_bits(t) or [t])

    for t in expanded:
        raw = t.strip()
        low = clean_token(raw).lower()
        low = re.sub(r"^(remote|hybrid)\s*[-,:]?\s*", "", low).strip()
        low = re.sub(r"\s*[-,:]\s*(remote|hybrid)$", "", low).strip()

        c = norm_country(raw) or norm_country(low)
        if c:
            found.append(c)
            continue

        st = US_STATES.get(low)
        if st:
            found.append("USA")
            if not state:
                state = st
            continue

        if is_worldwide(raw) or is_worldwide(low):
            worldwide = True
            continue
        if is_multi_region(raw) or is_multi_region(low):
            multi = True
            continue
        if is_other_country(raw) or is_other_country(low):
            other_only_hits += 1
            continue

        if low and low not in WORLDWIDE_EXACT and not city:
            city = clean_token(raw)

    country = ""
    for pref in TARGET:
        if pref in found:
            country = pref
            break

    if country in TARGET_SET:
        return country, state, city if city and not norm_country(city) else "", True

    # specific non-target country restriction (even if also marked remote)
    if other_only_hits:
        return "", "", "", False
    # worldwide / multi-region / unknown city-only remote
    return "", state, city, True


def record(*, id_, title, company, country, state, city, remote, url, posted_at, source, description):
    title = strip_html(title)
    company = strip_html(company)
    url = (url or "").strip()
    if not url or not title:
        return None
    if country not in TARGET_SET:
        country = ""
    return {
        "id": str(id_),
        "title": title,
        "company": company,
        "country": country,
        "state": state or "",
        "city": city or "",
        "remote": bool(remote),
        "url": url,
        "posted_at": posted_at,
        "source": source,
        "description": description or "",
    }


def write_jsonl(path, rows):
    seen = set()
    out = []
    for r in rows:
        if not r:
            continue
        url = (r.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(r)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm_rfj():
    rows = []
    raw_n = 0
    dropped = 0
    for i in range(5):
        p = RAW / f"rfj_p{i}.json"
        d = load_json(p)
        jobs = d.get("jobs") or []
        raw_n += len(jobs)
        for j in jobs:
            locs = j.get("locations") or []
            c, st, ci, keep = parse_locs(locs)
            if not keep:
                dropped += 1
                continue
            rec = record(
                id_=f"remotefirstjobs:{j.get('id') or ''}",
                title=j.get("title") or "",
                company=j.get("company_name") or "",
                country=c, state=st, city=ci,
                remote=True,
                url=j.get("url") or "",
                posted_at=parse_posted_at(j.get("published_at")),
                source="remotefirstjobs",
                description=short_desc(j.get("description") or ""),
            )
            if rec:
                rows.append(rec)
            else:
                dropped += 1
    out = write_jsonl(OUT / "remotefirstjobs.jsonl", rows)
    return {"raw": raw_n, "kept": len(out), "dropped": dropped, "countries": Counter(r["country"] or "(blank)" for r in out)}


def norm_wn():
    jobs = load_json(RAW / "workingnomads.json")
    if not isinstance(jobs, list):
        jobs = []
    rows = []
    dropped = 0
    for j in jobs:
        loc = j.get("location") or ""
        c, st, ci, keep = parse_locs([loc])
        if not keep:
            dropped += 1
            continue
        url = j.get("url") or ""
        slug = url.rstrip("/").split("/")[-1] if url else ""
        rec = record(
            id_=f"workingnomads:{slug or url}",
            title=j.get("title") or "",
            company=j.get("company_name") or "",
            country=c, state=st, city=ci,
            remote=True,
            url=url,
            posted_at=parse_posted_at(j.get("pub_date")),
            source="workingnomads",
            description=short_desc(j.get("description") or ""),
        )
        if rec:
            rows.append(rec)
        else:
            dropped += 1
    out = write_jsonl(OUT / "workingnomads.jsonl", rows)
    return {"raw": len(jobs), "kept": len(out), "dropped": dropped, "countries": Counter(r["country"] or "(blank)" for r in out)}


def norm_rjo():
    rows = []
    raw_n = 0
    dropped = 0
    for i in range(20):
        p = RAW / f"remotejobsorg_p{i}.json"
        if not p.exists():
            break
        d = load_json(p)
        jobs = d.get("data") or []
        raw_n += len(jobs)
        for j in jobs:
            loc = j.get("location") or ""
            c, st, ci, keep = parse_locs([loc])
            if not keep:
                dropped += 1
                continue
            comp = j.get("company")
            if isinstance(comp, dict):
                company = comp.get("name") or ""
            else:
                company = str(comp or "")
            rec = record(
                id_=f"remotejobsorg:{j.get('id') or ''}",
                title=j.get("title") or "",
                company=company,
                country=c, state=st, city=ci,
                remote=True,
                url=j.get("url") or j.get("apply_url") or "",
                posted_at=parse_posted_at(j.get("posted_at")),
                source="remotejobsorg",
                description=short_desc(j.get("description") or ""),
            )
            if rec:
                rows.append(rec)
            else:
                dropped += 1
    out = write_jsonl(OUT / "remotejobsorg.jsonl", rows)
    return {"raw": raw_n, "kept": len(out), "dropped": dropped, "countries": Counter(r["country"] or "(blank)" for r in out)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "remotefirstjobs": norm_rfj(),
        "workingnomads": norm_wn(),
        "remotejobsorg": norm_rjo(),
    }
    print(json.dumps(report, indent=2, default=lambda x: dict(x) if isinstance(x, Counter) else x))


if __name__ == "__main__":
    main()

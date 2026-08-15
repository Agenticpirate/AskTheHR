#!/usr/bin/env python3
"""Parse all raw job dumps into per-source JSONL. Does not fetch APIs."""
from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timezone, date
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from xml.etree import ElementTree as ET

RAW = Path("/workspace/jobs/raw")
NORM = Path("/workspace/jobs/normalized")

ALLOWED = {
    "USA", "India", "Canada", "UK", "Australia",
    "Germany", "Netherlands", "Ireland", "Singapore", "France",
}

SCHEMA = (
    "id", "title", "company", "country", "state", "city",
    "remote", "url", "posted_at", "source", "description",
)

COUNTRY_ALIASES = {
    "usa": "USA", "us": "USA", "u.s": "USA", "u.s.a": "USA",
    "united states": "USA", "united states of america": "USA", "america": "USA",
    "india": "India", "bharat": "India",
    "canada": "Canada",
    "uk": "UK", "u.k": "UK", "united kingdom": "UK", "great britain": "UK",
    "britain": "UK", "england": "UK", "scotland": "UK", "wales": "UK",
    "northern ireland": "UK",
    "united kingdom of great britain and northern ireland": "UK",
    "australia": "Australia",
    "germany": "Germany", "deutschland": "Germany",
    "federal republic of germany": "Germany",
    "netherlands": "Netherlands", "the netherlands": "Netherlands", "holland": "Netherlands",
    "ireland": "Ireland", "republic of ireland": "Ireland", "eire": "Ireland",
    "singapore": "Singapore",
    "france": "France",
}

ISO_COUNTRY = {
    "US": "USA", "USA": "USA",
    "GB": "UK", "UK": "UK",
    "IN": "India",
    "CA": "Canada",
    "AU": "Australia",
    "DE": "Germany",
    "NL": "Netherlands",
    "IE": "Ireland",
    "SG": "Singapore",
    "FR": "France",
}

CITY_COUNTRY = {
    "berlin": "Germany", "munich": "Germany", "münchen": "Germany", "muenchen": "Germany",
    "hamburg": "Germany", "köln": "Germany", "koln": "Germany", "cologne": "Germany",
    "frankfurt": "Germany", "frankfurt am main": "Germany", "düsseldorf": "Germany",
    "dusseldorf": "Germany", "stuttgart": "Germany", "leipzig": "Germany",
    "dresden": "Germany", "hannover": "Germany", "hanover": "Germany",
    "nürnberg": "Germany", "nuremberg": "Germany", "nurnberg": "Germany",
    "bremen": "Germany", "essen": "Germany", "dortmund": "Germany", "bonn": "Germany",
    "münster": "Germany", "mainz": "Germany", "wiesbaden": "Germany",
    "freiburg": "Germany", "karlsruhe": "Germany", "augsburg": "Germany",
    "mannheim": "Germany", "aachen": "Germany", "kiel": "Germany",
    "heidelberg": "Germany", "regensburg": "Germany", "würzburg": "Germany",
    "göttingen": "Germany", "darmstadt": "Germany", "bielefeld": "Germany",
    "bochum": "Germany", "wuppertal": "Germany", "erlangen": "Germany",
    "ingolstadt": "Germany", "ulm": "Germany", "jena": "Germany", "kassel": "Germany",
    "potsdam": "Germany", "saarbrücken": "Germany", "lübeck": "Germany",
    "eching": "Germany", "bayern": "Germany", "bavaria": "Germany",
    "london": "UK", "manchester": "UK", "birmingham": "UK", "glasgow": "UK",
    "edinburgh": "UK", "cardiff": "UK", "leeds": "UK", "bristol": "UK",
    "liverpool": "UK", "newcastle": "UK", "sheffield": "UK", "belfast": "UK",
    "brighton": "UK", "oxford": "UK", "cambridge": "UK", "reading": "UK",
    "nottingham": "UK", "leicester": "UK", "aberdeen": "UK", "southampton": "UK",
    "mayfair": "UK", "slough": "UK", "croydon": "UK", "milton keynes": "UK",
    "dublin": "Ireland", "cork": "Ireland", "galway": "Ireland", "limerick": "Ireland",
    "amsterdam": "Netherlands", "rotterdam": "Netherlands", "the hague": "Netherlands",
    "den haag": "Netherlands", "utrecht": "Netherlands", "eindhoven": "Netherlands",
    "paris": "France", "lyon": "France", "marseille": "France", "toulouse": "France",
    "nice": "France", "bordeaux": "France", "nantes": "France", "lille": "France",
    "sydney": "Australia", "melbourne": "Australia", "brisbane": "Australia",
    "perth": "Australia", "adelaide": "Australia", "canberra": "Australia",
    "toronto": "Canada", "vancouver": "Canada", "montreal": "Canada",
    "montréal": "Canada", "calgary": "Canada", "ottawa": "Canada",
    "edmonton": "Canada", "mississauga": "Canada", "waterloo": "Canada",
    "bangalore": "India", "bengaluru": "India", "mumbai": "India", "delhi": "India",
    "new delhi": "India", "hyderabad": "India", "chennai": "India", "pune": "India",
    "gurgaon": "India", "gurugram": "India", "noida": "India", "kolkata": "India",
    "ahmedabad": "India",
    "singapore": "Singapore",
    "new york": "USA", "nyc": "USA", "new york city": "USA",
    "san francisco": "USA", "los angeles": "USA", "seattle": "USA",
    "austin": "USA", "boston": "USA", "chicago": "USA", "denver": "USA",
    "atlanta": "USA", "miami": "USA", "dallas": "USA", "houston": "USA",
    "washington": "USA", "washington dc": "USA", "portland": "USA",
    "philadelphia": "USA", "phoenix": "USA", "san diego": "USA", "san jose": "USA",
    "palo alto": "USA", "mountain view": "USA", "sunnyvale": "USA", "redmond": "USA",
    "brooklyn": "USA", "manhattan": "USA", "sf": "USA",
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
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas", "ca": "California",
    "co": "Colorado", "ct": "Connecticut", "de": "Delaware", "fl": "Florida", "ga": "Georgia",
    "hi": "Hawaii", "id": "Idaho", "il": "Illinois", "ia": "Iowa", "ks": "Kansas",
    "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland", "ma": "Massachusetts",
    "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi", "mo": "Missouri", "mt": "Montana",
    "ne": "Nebraska", "nv": "Nevada", "nh": "New Hampshire", "nj": "New Jersey",
    "nm": "New Mexico", "ny": "New York", "nc": "North Carolina", "nd": "North Dakota",
    "oh": "Ohio", "ok": "Oklahoma", "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island",
    "sc": "South Carolina", "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas",
    "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington",
    "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming", "dc": "District of Columbia",
}

COMPANY_SPECIAL = {
    "openai": "OpenAI", "n8n": "n8n", "okta": "Okta",
    "andurilindustries": "Anduril", "bolcom": "bol.com", "boxinc": "Box",
    "gongio": "Gong", "grafanalabs": "Grafana Labs", "remotecom": "Remote",
    "riotgames": "Riot Games", "rocketlab": "Rocket Lab", "scaleai": "Scale AI",
    "shifttechnology": "Shift Technology", "traderepublic": "Trade Republic",
    "tldraw": "tldraw", "workos": "WorkOS", "posthog": "PostHog",
    "superhuman": "Superhuman", "character": "Character.AI",
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


def pretty_company(slug: str) -> str:
    s = (slug or "").strip()
    if not s:
        return ""
    key = s.lower().replace("-", "").replace("_", "")
    # try raw slug first
    if s.lower() in COMPANY_SPECIAL:
        return COMPANY_SPECIAL[s.lower()]
    if key in COMPANY_SPECIAL:
        return COMPANY_SPECIAL[key]
    return re.sub(r"[-_]+", " ", s).strip().title()


def load_json(path: Path):
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not raw or not raw.strip():
        return None
    s = raw.lstrip()
    if s.startswith(b"<") or s.lower().startswith(b"<!doctype"):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def is_error_payload(data) -> bool:
    if data is None:
        return True
    if isinstance(data, list):
        return False
    if not isinstance(data, dict):
        return True
    if data.get("jobs") is not None or data.get("data") is not None or data.get("results") is not None:
        return False
    if data.get("error") or data.get("ok") is False or data.get("success") is False:
        return True
    if data.get("status") in (404, 400, 403, 500, "404", "400", "403", "500"):
        return True
    return False


def canon_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        p = urlparse(raw)
    except Exception:
        return raw.rstrip("/").lower()
    host = (p.netloc or "").lower()
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(p.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")
        ]
    )
    path = p.path.rstrip("/")
    return urlunparse((p.scheme, host, path, p.params, query, p.fragment))


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts, timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    s = str(value).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{9,13}", s):
        return parse_date(int(s))
    try:
        ss = s[:-1] + "+00:00" if s.endswith("Z") else s
        return datetime.fromisoformat(ss).date()
    except Exception:
        pass
    try:
        return parsedate_to_datetime(s).date()
    except Exception:
        pass
    m = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def iso_date(value) -> str | None:
    d = parse_date(value)
    return d.isoformat() if d else None


def clean_token(token):
    t = (token or "").strip()
    t = re.sub(r"[\U0001F1E0-\U0001F1FF]", "", t)
    t = re.sub(r"\s+", " ", t).strip(" \t.,;:-")
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    return t


def norm_country(token):
    t = clean_token(token).lower()
    t = t.replace(".", "")
    t = re.sub(r"\s+", " ", t).strip()
    return COUNTRY_ALIASES.get(t)


def is_worldwide(token):
    t = clean_token(token).lower()
    if not t:
        return False
    keys = (
        "worldwide", "anywhere", "anywhere in the world", "global",
        "remote", "remote job", "work from home", "wfh", "fully remote",
        "100% remote", "international", "flexible / remote", "flexible/remote",
        "unrestricted",
    )
    if t in keys:
        return True
    if "anywhere" in t or "worldwide" in t or "work from home" in t:
        return True
    if t in ("flexible", "distributed"):
        return True
    return False


def lookup_city(token):
    t = clean_token(token).lower()
    t = t.replace(" hq", "").replace(" headquarters", "").strip(" ,;/-")
    t = re.sub(r"\s+", " ", t)
    if t in CITY_COUNTRY:
        return CITY_COUNTRY[t]
    for city, ctry in CITY_COUNTRY.items():
        if t.startswith(city + " ") or t.endswith(" " + city):
            return ctry
    for city, ctry in CITY_COUNTRY.items():
        if len(city) >= 4 and re.search(r"\b" + re.escape(city) + r"\b", t):
            return ctry
    return None


def looks_remote_text(text) -> bool:
    if not text:
        return False
    low = str(text).lower()
    return bool(re.search(
        r"\bremote\b|\bwfh\b|work from home|work-from-home|worldwide|"
        r"anywhere|telecommute|distributed|flexible\s*/\s*remote",
        low,
    ))


def parse_location(location):
    """Return country, state, city, looks_remote."""
    if not location:
        return "", "", "", False
    raw = str(location)
    low = raw.lower()
    looks_remote = looks_remote_text(raw)
    raw2 = re.sub(r"\band\b", ",", raw, flags=re.I)
    parts = [p.strip() for p in re.split(r"[,;/|]+|\s+OR\s+", raw2) if p.strip()]
    found = []
    state = ""
    city = ""
    for p in parts:
        c = norm_country(p)
        if c:
            found.append(c)
            continue
        if is_worldwide(p):
            continue
        # skip leftover remote-prefixed tokens like "Remote US" already split
        p_clean = re.sub(r"(?i)^(remote|hybrid|onsite|on-site|in-office)\s*[-–: ]*", "", p).strip()
        c = norm_country(p_clean)
        if c:
            found.append(c)
            continue
        cc = lookup_city(p_clean or p)
        if cc:
            found.append(cc)
            cand = clean_token(p_clean or p)
            if cand and not norm_country(cand) and not is_worldwide(cand) and not city:
                city = cand
            continue
        st = US_STATES.get(clean_token(p_clean or p).lower())
        if st:
            found.append("USA")
            if not state:
                state = st
            continue
        if not city and clean_token(p_clean or p) and not is_worldwide(p_clean or p):
            city = clean_token(p_clean or p)
    country = found[0] if found else ""
    if city and (norm_country(city) or is_worldwide(city) or city.lower() in ("remote", "hybrid", "anywhere")):
        city = ""
    if state and (norm_country(state) or state.lower() in ("remote", "hybrid")):
        state = ""
    return country, state, city, looks_remote


def keep_job(country, remote):
    if remote:
        return country in ALLOWED or country == ""
    return country in ALLOWED


def slug_from_url(url):
    if not url:
        return ""
    return url.rstrip("/").split("/")[-1] or ""


def make_rec(*, source, native_id, title, company, country, state, city,
             remote, url, posted_at, description):
    url = (url or "").strip()
    if not url or not (title or "").strip():
        return None
    country = country if country in ALLOWED else ""
    if not keep_job(country, bool(remote)):
        return None
    return {
        "id": f"{source}:{native_id}" if native_id else f"{source}:{slug_from_url(url)}",
        "title": strip_html(title)[:300],
        "company": strip_html(company),
        "country": country,
        "state": (state or "")[:80],
        "city": (city or "")[:80],
        "remote": bool(remote),
        "url": url,
        "posted_at": posted_at,
        "source": source,
        "description": short_desc(description or title),
    }


def write_jsonl(path: Path, rows):
    seen = set()
    out = []
    for r in rows:
        if not r:
            continue
        key = canon_url(r.get("url") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        rec = {k: r.get(k) if k != "remote" else bool(r.get("remote")) for k in SCHEMA}
        rec["url"] = (r.get("url") or "").strip()
        rec["id"] = rec["id"] or ""
        rec["title"] = rec["title"] or ""
        rec["company"] = rec["company"] or ""
        rec["country"] = rec["country"] or ""
        rec["state"] = rec["state"] or ""
        rec["city"] = rec["city"] or ""
        rec["source"] = rec["source"] or ""
        rec["description"] = rec["description"] or ""
        out.append(rec)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)
    return out


def localname(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse_rss_items(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        xml_text = re.sub(r"&(?!amp;|lt;|gt;|apos;|quot;|#)", "&amp;", xml_text)
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return items
    for el in root.iter():
        if localname(el.tag) not in ("item", "entry"):
            continue
        fields = {}
        for c in list(el):
            key = localname(c.tag)
            val = "".join(c.itertext())
            if key not in fields:
                fields[key] = val
        items.append(fields)
    return items


# ---------------------------------------------------------------------------
# Source parsers
# ---------------------------------------------------------------------------

def parse_greenhouse():
    rows = []
    files = sorted(RAW.glob("gh_*.json"))
    used = skipped = 0
    for path in files:
        data = load_json(path)
        if is_error_payload(data):
            skipped += 1
            continue
        used += 1
        board = path.stem[3:]  # gh_
        company_fallback = pretty_company(board)
        jobs = data.get("jobs") if isinstance(data, dict) else []
        if not isinstance(jobs, list):
            continue
        for j in jobs:
            if not isinstance(j, dict):
                continue
            loc = j.get("location") or {}
            loc_name = loc.get("name") if isinstance(loc, dict) else str(loc or "")
            offices = j.get("offices") or []
            office_bits = []
            for off in offices:
                if isinstance(off, dict):
                    office_bits.append(off.get("name") or "")
                    loc2 = off.get("location")
                    if isinstance(loc2, dict):
                        office_bits.append(loc2.get("name") or "")
                    elif loc2:
                        office_bits.append(str(loc2))
            loc_text = ", ".join(x for x in [loc_name] + office_bits if x)
            country, state, city, loc_remote = parse_location(loc_text)
            remote = loc_remote
            rec = make_rec(
                source="greenhouse",
                native_id=f"{board}:{j.get('id')}",
                title=j.get("title") or "",
                company=j.get("company_name") or company_fallback,
                country=country, state=state, city=city, remote=remote,
                url=j.get("absolute_url") or "",
                posted_at=iso_date(j.get("first_published") or j.get("updated_at")),
                description=j.get("content") or j.get("title") or "",
            )
            if rec:
                rows.append(rec)
    print(f"  greenhouse files used={used} skipped={skipped} raw_boards={len(files)} kept_pre_dedup={len(rows)}")
    return rows


def parse_lever():
    rows = []
    files = sorted(RAW.glob("lever_*.json"))
    used = skipped = 0
    for path in files:
        data = load_json(path)
        if is_error_payload(data) or not isinstance(data, list):
            skipped += 1
            continue
        used += 1
        board = path.stem[6:]  # lever_
        company = pretty_company(board)
        for j in data:
            if not isinstance(j, dict):
                continue
            cats = j.get("categories") or {}
            loc = cats.get("location") or ""
            all_locs = cats.get("allLocations") or []
            loc_text = ", ".join([str(loc)] + [str(x) for x in all_locs if x])
            country, state, city, loc_remote = parse_location(loc_text)
            iso = ISO_COUNTRY.get(str(j.get("country") or "").strip().upper())
            if iso and not country:
                country = iso
            elif iso and country not in ALLOWED:
                country = iso
            wt = str(j.get("workplaceType") or "").lower()
            remote = loc_remote or wt in ("remote", "hybrid")
            rec = make_rec(
                source="lever",
                native_id=f"{board}:{j.get('id')}",
                title=j.get("text") or "",
                company=company,
                country=country, state=state, city=city, remote=remote,
                url=j.get("hostedUrl") or j.get("applyUrl") or "",
                posted_at=iso_date(j.get("createdAt")),
                description=j.get("descriptionPlain") or j.get("openingPlain") or j.get("text") or "",
            )
            if rec:
                rows.append(rec)
    print(f"  lever files used={used} skipped={skipped} kept_pre_dedup={len(rows)}")
    return rows


def parse_ashby():
    rows = []
    files = sorted(RAW.glob("ashby_*.json"))
    used = skipped = 0
    for path in files:
        data = load_json(path)
        if is_error_payload(data):
            skipped += 1
            continue
        used += 1
        board = path.stem[6:]  # ashby_
        company = pretty_company(board)
        jobs = data.get("jobs") if isinstance(data, dict) else []
        if not isinstance(jobs, list):
            continue
        for j in jobs:
            if not isinstance(j, dict):
                continue
            loc = j.get("location") or ""
            sec = j.get("secondaryLocations") or []
            extra = []
            for s in sec:
                if isinstance(s, dict):
                    extra.append(s.get("location") or s.get("name") or "")
                else:
                    extra.append(str(s))
            loc_text = ", ".join(x for x in [str(loc)] + extra if x)
            country, state, city, loc_remote = parse_location(loc_text)
            wt = str(j.get("workplaceType") or "")
            is_remote = j.get("isRemote")
            remote = bool(is_remote) or loc_remote or wt.lower() in ("remote", "hybrid")
            rec = make_rec(
                source="ashby",
                native_id=f"{board}:{j.get('id')}",
                title=j.get("title") or "",
                company=company,
                country=country, state=state, city=city, remote=remote,
                url=j.get("jobUrl") or j.get("applyUrl") or "",
                posted_at=iso_date(j.get("publishedAt")),
                description=j.get("descriptionPlain") or j.get("descriptionHtml") or j.get("title") or "",
            )
            if rec:
                rows.append(rec)
    print(f"  ashby files used={used} skipped={skipped} kept_pre_dedup={len(rows)}")
    return rows


def parse_himalayas():
    rows = []
    files = sorted(RAW.glob("himalayas*.json"))
    used = skipped = 0
    n_raw = 0
    for i, path in enumerate(files, 1):
        data = load_json(path)
        if is_error_payload(data):
            skipped += 1
            continue
        used += 1
        jobs = data.get("jobs") if isinstance(data, dict) else []
        if not isinstance(jobs, list):
            continue
        n_raw += len(jobs)
        for j in jobs:
            if not isinstance(j, dict):
                continue
            restrictions = j.get("locationRestrictions") or []
            if isinstance(restrictions, str):
                restrictions = [restrictions]
            found = []
            worldwide = not restrictions
            for r in restrictions:
                c = norm_country(str(r))
                if c:
                    found.append(c)
                elif is_worldwide(str(r)):
                    worldwide = True
            if found:
                allowed_found = [c for c in found if c in ALLOWED]
                if not allowed_found:
                    continue
                country = allowed_found[0]
            else:
                country = ""
                if restrictions and not worldwide:
                    continue
            company = j.get("companyName") or ""
            if str(company).strip().lower() in {"name", "n/a", "null", "", "company", "thumbnail_url"}:
                company = pretty_company(j.get("companySlug") or "")
            url = j.get("applicationLink") or j.get("guid") or ""
            rec = make_rec(
                source="himalayas",
                native_id=slug_from_url(j.get("guid") or url),
                title=j.get("title") or "",
                company=company,
                country=country, state="", city="", remote=True,
                url=url,
                posted_at=iso_date(j.get("pubDate")),
                description=j.get("excerpt") or j.get("description") or "",
            )
            if rec:
                rows.append(rec)
        if i % 100 == 0:
            print(f"  himalayas progress {i}/{len(files)} files, raw_jobs={n_raw}, kept_pre={len(rows)}")
    print(f"  himalayas files used={used} skipped={skipped} raw_jobs={n_raw} kept_pre_dedup={len(rows)}")
    return rows


def parse_themuse():
    rows = []
    files = sorted(RAW.glob("themuse*.json"))
    used = skipped = 0
    n_raw = 0
    for path in files:
        data = load_json(path)
        if is_error_payload(data):
            skipped += 1
            continue
        used += 1
        results = data.get("results") if isinstance(data, dict) else []
        if not isinstance(results, list):
            continue
        n_raw += len(results)
        for j in results:
            if not isinstance(j, dict):
                continue
            locs = j.get("locations") or []
            loc_names = []
            for loc in locs:
                if isinstance(loc, dict):
                    loc_names.append(loc.get("name") or "")
                else:
                    loc_names.append(str(loc))
            loc_text = ", ".join(x for x in loc_names if x)
            country, state, city, loc_remote = parse_location(loc_text)
            remote = loc_remote
            company = ""
            if isinstance(j.get("company"), dict):
                company = j["company"].get("name") or ""
            url = ""
            if isinstance(j.get("refs"), dict):
                url = j["refs"].get("landing_page") or ""
            rec = make_rec(
                source="themuse",
                native_id=j.get("id"),
                title=j.get("name") or j.get("title") or "",
                company=company,
                country=country, state=state, city=city, remote=remote,
                url=url,
                posted_at=iso_date(j.get("publication_date")),
                description=j.get("contents") or "",
            )
            if rec:
                rows.append(rec)
    print(f"  themuse files used={used} skipped={skipped} raw_jobs={n_raw} kept_pre_dedup={len(rows)}")
    return rows


def parse_arbeitnow():
    """Keep ONLY remote=true rows (drop on-site Arbeitnow)."""
    rows = []
    files = sorted(RAW.glob("arbeitnow*.json"))
    used = skipped = 0
    n_raw = n_remote = 0
    for path in files:
        data = load_json(path)
        if is_error_payload(data):
            skipped += 1
            continue
        used += 1
        jobs = []
        if isinstance(data, dict):
            if isinstance(data.get("jobs"), list):
                jobs = data["jobs"]
            elif isinstance(data.get("data"), list):
                jobs = data["data"]
        n_raw += len(jobs)
        for j in jobs:
            if not isinstance(j, dict):
                continue
            if not j.get("remote"):
                continue
            n_remote += 1
            loc = j.get("location") or ""
            country, state, city, loc_remote = parse_location(loc)
            rec = make_rec(
                source="arbeitnow",
                native_id=j.get("slug") or slug_from_url(j.get("url") or ""),
                title=j.get("title") or "",
                company=j.get("company_name") or "",
                country=country, state=state, city=city, remote=True,
                url=j.get("url") or "",
                posted_at=iso_date(j.get("created_at")),
                description=j.get("description") or "",
            )
            if rec:
                rows.append(rec)
    print(f"  arbeitnow files used={used} skipped={skipped} raw={n_raw} remote_flag={n_remote} kept_pre_dedup={len(rows)}")
    return rows


def parse_remoteok():
    rows = []
    path = RAW / "remoteok.json"
    data = load_json(path)
    if is_error_payload(data) or not isinstance(data, list):
        print("  remoteok skipped (error/empty)")
        return rows
    for j in data:
        if not isinstance(j, dict) or not j.get("id") or "legal" in j:
            continue
        loc = j.get("location") or ""
        country, state, city, _ = parse_location(loc)
        rec = make_rec(
            source="remoteok",
            native_id=j.get("id") or j.get("slug"),
            title=j.get("position") or j.get("title") or "",
            company=j.get("company") or "",
            country=country, state=state, city=city, remote=True,
            url=j.get("url") or j.get("apply_url") or "",
            posted_at=iso_date(j.get("date") or j.get("epoch")),
            description=j.get("description") or "",
        )
        if rec:
            rows.append(rec)
    print(f"  remoteok kept_pre_dedup={len(rows)}")
    return rows


def parse_remotive():
    rows = []
    path = RAW / "remotive.json"
    data = load_json(path)
    if is_error_payload(data):
        print("  remotive skipped (error/empty)")
        return rows
    jobs = data.get("jobs") if isinstance(data, dict) else []
    for j in jobs or []:
        if not isinstance(j, dict):
            continue
        loc = j.get("candidate_required_location") or ""
        country, state, city, _ = parse_location(loc)
        rec = make_rec(
            source="remotive",
            native_id=j.get("id"),
            title=j.get("title") or "",
            company=j.get("company_name") or "",
            country=country, state=state, city=city, remote=True,
            url=j.get("url") or "",
            posted_at=iso_date(j.get("publication_date")),
            description=j.get("description") or "",
        )
        if rec:
            rows.append(rec)
    print(f"  remotive kept_pre_dedup={len(rows)}")
    return rows


def parse_jobicy():
    rows = []
    files = sorted(RAW.glob("jobicy*.json"))
    used = skipped = 0
    for path in files:
        data = load_json(path)
        if is_error_payload(data):
            skipped += 1
            continue
        used += 1
        jobs = data.get("jobs") if isinstance(data, dict) else []
        if not isinstance(jobs, list):
            continue
        for j in jobs:
            if not isinstance(j, dict):
                continue
            geo = j.get("jobGeo") or ""
            country, state, city, _ = parse_location(geo)
            rec = make_rec(
                source="jobicy",
                native_id=j.get("id"),
                title=j.get("jobTitle") or "",
                company=j.get("companyName") or "",
                country=country, state=state, city=city, remote=True,
                url=j.get("url") or "",
                posted_at=iso_date(j.get("pubDate")),
                description=j.get("jobExcerpt") or j.get("jobDescription") or "",
            )
            if rec:
                rows.append(rec)
    print(f"  jobicy files used={used} skipped={skipped} kept_pre_dedup={len(rows)}")
    return rows


def parse_wwr():
    rows = []
    seen_links = set()
    items = []
    for name in ("wwr.rss.xml", "wwr.rss"):
        path = RAW / name
        if not path.exists() or path.stat().st_size == 0:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip() or text.lstrip().lower().startswith("<html"):
            continue
        chunks = re.split(r"<!-- FEED .*? -->\n", text)
        if len(chunks) <= 1:
            chunks = [text]
        for ch in chunks:
            ch = ch.strip()
            if not ch:
                continue
            if not (ch.startswith("<?xml") or "<rss" in ch[:300] or "<feed" in ch[:300]):
                # still try if it looks like leftover xml
                if "<item>" not in ch and "<entry>" not in ch:
                    continue
            try:
                parsed = parse_rss_items(ch)
            except Exception as e:
                print("  WWR parse error", e)
                continue
            for it in parsed:
                link = (it.get("link") or it.get("guid") or "").strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                items.append(it)
    for it in items:
        title_raw = (it.get("title") or "").strip()
        company, title = "", title_raw
        if ":" in title_raw:
            company, rest = title_raw.split(":", 1)
            company, title = company.strip(), (rest.strip() or title_raw)
        loc_bits = " ".join(filter(None, [it.get("country") or "", it.get("region") or "", it.get("state") or ""]))
        desc = it.get("description") or it.get("summary") or ""
        hq = ""
        m = re.search(r"Headquarters:</strong>\s*([^<]+)", desc, re.I)
        if m:
            hq = html.unescape(m.group(1)).strip()
        country, state, city, _ = parse_location(loc_bits)
        if hq:
            hq_country, hq_state, hq_city, _ = parse_location(hq.replace(" - ", ", ").replace(" – ", ", "))
            country = country or hq_country
            state = state or hq_state
            city = city or hq_city
        if not country:
            c2 = norm_country(it.get("country") or "")
            if c2:
                country = c2
        rss_state = (it.get("state") or "").strip()
        if rss_state and not city:
            city = rss_state
        region = (it.get("region") or "").strip()
        if region and region.lower() in US_STATES:
            country = country or "USA"
            state = state or US_STATES[region.lower()]
        if rss_state and rss_state.lower() in US_STATES:
            country = country or "USA"
            state = state or US_STATES[rss_state.lower()]
            if city == rss_state:
                city = ""
        rec = make_rec(
            source="weworkremotely",
            native_id=slug_from_url((it.get("link") or it.get("guid") or "").strip()),
            title=title,
            company=company,
            country=country, state=state,
            city=city if city and not norm_country(city) else "",
            remote=True,
            url=(it.get("link") or it.get("guid") or "").strip(),
            posted_at=iso_date(it.get("pubDate") or it.get("published") or it.get("updated")),
            description=desc,
        )
        if rec:
            rows.append(rec)
    print(f"  weworkremotely unique_items={len(items)} kept_pre_dedup={len(rows)}")
    return rows


def main():
    NORM.mkdir(parents=True, exist_ok=True)
    parsers = [
        ("greenhouse", parse_greenhouse),
        ("lever", parse_lever),
        ("ashby", parse_ashby),
        ("himalayas", parse_himalayas),
        ("themuse", parse_themuse),
        ("arbeitnow", parse_arbeitnow),
        ("remoteok", parse_remoteok),
        ("remotive", parse_remotive),
        ("jobicy", parse_jobicy),
        ("weworkremotely", parse_wwr),
    ]
    counts = {}
    for name, fn in parsers:
        print(f"=== {name} ===", flush=True)
        rows = fn()
        out = write_jsonl(NORM / f"{name}.jsonl", rows)
        counts[name] = len(out)
        print(f"  wrote {len(out)} -> {NORM / (name + '.jsonl')}", flush=True)
    print("PER_SOURCE", json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

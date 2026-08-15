#!/usr/bin/env python3
"""Pull public Greenhouse + Lever ATS jobs, normalize, write JSONL."""

from __future__ import annotations

import html
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

# --- config ---
UA = "Mozilla/5.0 (compatible; JobCollector/1.0)"
TIMEOUT = 2.0
DELAY_LO, DELAY_HI = 0.15, 0.25
TIME_BUDGET_SEC = 480  # ~8 minutes of fetching
RETRY_429_WAIT = 2.0
TODAY = date(2026, 8, 15)
AUG_START = date(2026, 8, 1)
AUG_END = date(2026, 9, 1)
FALLBACK_START = date(2026, 5, 17)  # 90 days before 2026-08-15

ROOT = Path("/workspace/jobs")
RAW_DIR = ROOT / "raw"
NORM_DIR = ROOT / "normalized"
LOG_PATH = RAW_DIR / "ats_boards.log"
GH_OUT = NORM_DIR / "greenhouse.jsonl"
LV_OUT = NORM_DIR / "lever.jsonl"
GH_SAMPLE = RAW_DIR / "greenhouse_sample.json"

TARGET_COUNTRIES = {
    "USA",
    "India",
    "Canada",
    "UK",
    "Australia",
    "Germany",
    "Netherlands",
    "Ireland",
    "Singapore",
    "France",
}

REMOTE_RE = re.compile(
    r"\b(remote|anywhere|distributed|work[\s-]?from[\s-]?home|wfh|workfromhome)\b",
    re.I,
)

US_STATES = {
    "al": "Alabama",
    "ak": "Alaska",
    "az": "Arizona",
    "ar": "Arkansas",
    "ca": "California",
    "co": "Colorado",
    "ct": "Connecticut",
    "de": "Delaware",
    "fl": "Florida",
    "ga": "Georgia",
    "hi": "Hawaii",
    "id": "Idaho",
    "il": "Illinois",
    "in": "Indiana",
    "ia": "Iowa",
    "ks": "Kansas",
    "ky": "Kentucky",
    "la": "Louisiana",
    "me": "Maine",
    "md": "Maryland",
    "ma": "Massachusetts",
    "mi": "Michigan",
    "mn": "Minnesota",
    "ms": "Mississippi",
    "mo": "Missouri",
    "mt": "Montana",
    "ne": "Nebraska",
    "nv": "Nevada",
    "nh": "New Hampshire",
    "nj": "New Jersey",
    "nm": "New Mexico",
    "ny": "New York",
    "nc": "North Carolina",
    "nd": "North Dakota",
    "oh": "Ohio",
    "ok": "Oklahoma",
    "or": "Oregon",
    "pa": "Pennsylvania",
    "ri": "Rhode Island",
    "sc": "South Carolina",
    "sd": "South Dakota",
    "tn": "Tennessee",
    "tx": "Texas",
    "ut": "Utah",
    "vt": "Vermont",
    "va": "Virginia",
    "wa": "Washington",
    "wv": "West Virginia",
    "wi": "Wisconsin",
    "wy": "Wyoming",
    "dc": "District of Columbia",
}
US_STATE_NAMES = {v.lower(): v for v in US_STATES.values()}
US_STATE_NAMES["washington dc"] = "District of Columbia"
US_STATE_NAMES["washington d.c."] = "District of Columbia"
US_STATE_NAMES["d.c."] = "District of Columbia"

# City → country (lowercase). Ambiguous US/other handled separately.
CITY_COUNTRY = {
    # India
    "bengaluru": "India",
    "bangalore": "India",
    "hyderabad": "India",
    "mumbai": "India",
    "delhi": "India",
    "new delhi": "India",
    "pune": "India",
    "chennai": "India",
    "gurgaon": "India",
    "gurugram": "India",
    "noida": "India",
    "kolkata": "India",
    "ahmedabad": "India",
    "jaipur": "India",
    "kochi": "India",
    "coimbatore": "India",
    "thiruvananthapuram": "India",
    "trivandrum": "India",
    "indore": "India",
    "chandigarh": "India",
    # Canada
    "toronto": "Canada",
    "vancouver": "Canada",
    "montreal": "Canada",
    "montréal": "Canada",
    "ottawa": "Canada",
    "calgary": "Canada",
    "edmonton": "Canada",
    "waterloo": "Canada",
    "mississauga": "Canada",
    "kitchener": "Canada",
    "victoria": "Canada",
    "winnipeg": "Canada",
    "quebec city": "Canada",
    "québec": "Canada",
    "halifax": "Canada",
    # UK
    "london": "UK",
    "manchester": "UK",
    "edinburgh": "UK",
    "belfast": "UK",
    "birmingham": "UK",
    "bristol": "UK",
    "leeds": "UK",
    "glasgow": "UK",
    "cambridge": "UK",
    "oxford": "UK",
    "cardiff": "UK",
    "reading": "UK",
    "brighton": "UK",
    # Australia
    "sydney": "Australia",
    "melbourne": "Australia",
    "brisbane": "Australia",
    "perth": "Australia",
    "canberra": "Australia",
    "adelaide": "Australia",
    "hobart": "Australia",
    "gold coast": "Australia",
    # Germany
    "berlin": "Germany",
    "munich": "Germany",
    "münchen": "Germany",
    "muenchen": "Germany",
    "hamburg": "Germany",
    "frankfurt": "Germany",
    "cologne": "Germany",
    "köln": "Germany",
    "koeln": "Germany",
    "stuttgart": "Germany",
    "düsseldorf": "Germany",
    "dusseldorf": "Germany",
    "leipzig": "Germany",
    "dortmund": "Germany",
    "aachen": "Germany",
    # Netherlands
    "amsterdam": "Netherlands",
    "rotterdam": "Netherlands",
    "the hague": "Netherlands",
    "den haag": "Netherlands",
    "utrecht": "Netherlands",
    "eindhoven": "Netherlands",
    "haarlem": "Netherlands",
    "groningen": "Netherlands",
    # Ireland
    "dublin": "Ireland",
    "cork": "Ireland",
    "galway": "Ireland",
    "limerick": "Ireland",
    "waterford": "Ireland",
    # Singapore
    "singapore": "Singapore",
    # France
    "paris": "France",
    "lyon": "France",
    "toulouse": "France",
    "nantes": "France",
    "bordeaux": "France",
    "marseille": "France",
    "lille": "France",
    "nice": "France",
    "grenoble": "France",
    # USA major (helps when no state)
    "new york": "USA",
    "new york city": "USA",
    "nyc": "USA",
    "san francisco": "USA",
    "sf": "USA",
    "los angeles": "USA",
    "seattle": "USA",
    "austin": "USA",
    "boston": "USA",
    "chicago": "USA",
    "denver": "USA",
    "atlanta": "USA",
    "miami": "USA",
    "dallas": "USA",
    "houston": "USA",
    "palo alto": "USA",
    "mountain view": "USA",
    "sunnyvale": "USA",
    "cupertino": "USA",
    "menlo park": "USA",
    "redwood city": "USA",
    "san jose": "USA",
    "san mateo": "USA",
    "oakland": "USA",
    "brooklyn": "USA",
    "manhattan": "USA",
    "washington": "USA",
    "washington dc": "USA",
    "portland": "USA",
    "philadelphia": "USA",
    "phoenix": "USA",
    "san diego": "USA",
    "minneapolis": "USA",
    "detroit": "USA",
    "pittsburgh": "USA",
    "salt lake city": "USA",
    "boulder": "USA",
    "raleigh": "USA",
    "durham": "USA",
    "nashville": "USA",
    "charlotte": "USA",
    "tampa": "USA",
    "orlando": "USA",
    "las vegas": "USA",
    "indianapolis": "USA",
    "columbus": "USA",
    "kansas city": "USA",
    "st. louis": "USA",
    "saint louis": "USA",
    "cambridge ma": "USA",
    "somerville": "USA",
    "bellevue": "USA",
    "redmond": "USA",
    "kirkland": "USA",
    "irvine": "USA",
    "santa monica": "USA",
    "venice": "USA",
    "brooklyn ny": "USA",
    "jersey city": "USA",
    "hoboken": "USA",
    "princeton": "USA",
    "ann arbor": "USA",
    "madison": "USA",
    "boulder co": "USA",
}

# Cities that should NOT use US-state "IN"/"CA"/"DE" as country
INDIA_CITIES = {
    "bengaluru",
    "bangalore",
    "hyderabad",
    "mumbai",
    "delhi",
    "new delhi",
    "pune",
    "chennai",
    "gurgaon",
    "gurugram",
    "noida",
    "kolkata",
    "ahmedabad",
}
CANADA_CITIES = {
    "toronto",
    "vancouver",
    "montreal",
    "montréal",
    "ottawa",
    "calgary",
    "edmonton",
    "waterloo",
    "mississauga",
    "kitchener",
    "winnipeg",
    "halifax",
}
GERMANY_CITIES = {
    "berlin",
    "munich",
    "münchen",
    "hamburg",
    "frankfurt",
    "cologne",
    "köln",
    "stuttgart",
    "düsseldorf",
}

COMPANY_NAMES = {
    "n26": "N26",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gitlab": "GitLab",
    "databricks": "Databricks",
    "snowflake": "Snowflake",
    "cloudflare": "Cloudflare",
    "coinbase": "Coinbase",
    "doordash": "DoorDash",
    "lyft": "Lyft",
    "uber": "Uber",
    "pinterest": "Pinterest",
    "reddit": "Reddit",
    "dropbox": "Dropbox",
    "atlassian": "Atlassian",
    "canva": "Canva",
    "intercom": "Intercom",
    "gusto": "Gusto",
    "lattice": "Lattice",
    "rippling": "Rippling",
    "plaid": "Plaid",
    "airtable": "Airtable",
    "asana": "Asana",
    "webflow": "Webflow",
    "grafana": "Grafana",
    "mongodb": "MongoDB",
    "hashicorp": "HashiCorp",
    "datadog": "Datadog",
    "okta": "Okta",
    "hubspot": "HubSpot",
    "spotify": "Spotify",
    "zendesk": "Zendesk",
    "wise": "Wise",
    "monzo": "Monzo",
    "adyen": "Adyen",
    "klarna": "Klarna",
    "nvidia": "NVIDIA",
    "tesla": "Tesla",
    "rivian": "Rivian",
    "huggingface": "Hugging Face",
    "mistral": "Mistral",
    "duolingo": "Duolingo",
    "airbnb": "Airbnb",
    "stripe": "Stripe",
    "discord": "Discord",
    "figma": "Figma",
    "notion": "Notion",
    "vercel": "Vercel",
    "twilio": "Twilio",
    "robinhood": "Robinhood",
    "instacart": "Instacart",
    "box": "Box",
    "zoom": "Zoom",
    "mercury": "Mercury",
    "ramp": "Ramp",
    "brex": "Brex",
    "linear": "Linear",
    "cursor": "Cursor",
    "monday": "Monday.com",
    "fivetran": "Fivetran",
    "dbt": "dbt Labs",
    "elastic": "Elastic",
    "crowdstrike": "CrowdStrike",
    "auth0": "Auth0",
    "sendgrid": "SendGrid",
    "supabase": "Supabase",
    "planetscale": "PlanetScale",
    "neon": "Neon",
    "railway": "Railway",
    "render": "Render",
    "gong": "Gong",
    "deel": "Deel",
    "odoo": "Odoo",
    "sap": "SAP",
    "siemens": "Siemens",
    "klaviyo": "Klaviyo",
    "revolut": "Revolut",
    "block": "Block",
    "square": "Square",
    "tiktok": "TikTok",
    "bytedance": "ByteDance",
    "amd": "AMD",
    "intel": "Intel",
    "arm": "Arm",
    "qualcomm": "Qualcomm",
    "waymo": "Waymo",
    "anduril": "Anduril",
    "palantir": "Palantir",
    "netflix": "Netflix",
    "shopify": "Shopify",
    "mixpanel": "Mixpanel",
    "amplitude": "Amplitude",
    "yelp": "Yelp",
    "quora": "Quora",
    "eventbrite": "Eventbrite",
    "medium": "Medium",
    "segment": "Segment",
    "kensho": "Kensho",
    "citadel": "Citadel",
    "optiver": "Optiver",
    "imc": "IMC",
    "drw": "DRW",
    "virtu": "Virtu",
    "lever": "Lever",
    "sourceday": "SourceDay",
    "kraken": "Kraken",
    "gemini": "Gemini",
    "sofi": "SoFi",
    "affirm": "Affirm",
    "toast": "Toast",
    "paypal": "PayPal",
    "salesforce": "Salesforce",
    "servicenow": "ServiceNow",
    "workday": "Workday",
    "intuit": "Intuit",
    "twitch": "Twitch",
    "roblox": "Roblox",
    "unity": "Unity",
    "coursera": "Coursera",
    "udemy": "Udemy",
    "expedia": "Expedia",
    "marriott": "Marriott",
    "hilton": "Hilton",
    "afterpay": "Afterpay",
    "cashapp": "Cash App",
    "spacex": "SpaceX",
    "blueorigin": "Blue Origin",
    "coreweave": "CoreWeave",
    "groq": "Groq",
    "cerebras": "Cerebras",
    "cohere": "Cohere",
    "perplexity": "Perplexity",
    "scale": "Scale AI",
    "palantirgh": "Palantir",
    "shopifygh": "Shopify",
    "notionhq": "Notion",
    "remotecom": "Remote",
    "remote-com": "Remote",
    "flyio": "Fly.io",
    "fly-io": "Fly.io",
    "calcom": "Cal.com",
    "cloudkitchens": "CloudKitchens",
    "jane-street": "Jane Street",
    "janestreet": "Jane Street",
    "two-sigma": "Two Sigma",
    "twosigma": "Two Sigma",
    "jumptrading": "Jump Trading",
    "hudson-river": "Hudson River Trading",
    "hrt": "Hudson River Trading",
    "flowtraders": "Flow Traders",
    "tower-research": "Tower Research",
    "de-shaw": "D. E. Shaw",
    "deshaw": "D. E. Shaw",
    "susquehanna": "Susquehanna",
    "sig": "Susquehanna",
    "renaissance": "Renaissance",
    "khanacademy": "Khan Academy",
    "khan-academy": "Khan Academy",
    "bookingcom": "Booking.com",
    "booking-com": "Booking.com",
    "riotgames": "Riot Games",
    "riot-games": "Riot Games",
    "epicgames": "Epic Games",
    "electronicarts": "Electronic Arts",
    "ea": "EA",
    "capitalone": "Capital One",
    "mastercard": "Mastercard",
    "amex": "American Express",
    "bigcommerce": "BigCommerce",
    "woocommerce": "WooCommerce",
    "service-now": "ServiceNow",
    "hex-technologies": "Hex",
    "hextechnologies": "Hex",
    "hex": "Hex",
    "characterai": "Character.AI",
    "midjourney": "Midjourney",
    "stability": "Stability AI",
    "together": "Together AI",
    "fireworks": "Fireworks AI",
    "sambanova": "SambaNova",
    "lambda": "Lambda",
    "crusoe": "Crusoe",
    "shieldai": "Shield AI",
    "rocketlab": "Rocket Lab",
    "relativity": "Relativity Space",
    "hadrian": "Hadrian",
    "scalesai": "Scale AI",
    "graviton": "Graviton",
    "gravitondata": "Graviton",
    "graviton-data": "Graviton",
    "gravitonhq": "Graviton",
    "toasttab": "Toast",
    "toast-tab": "Toast",
    "toastinc": "Toast",
    "lucid": "Lucid",
    "cruise": "Cruise",
    "soundcloud": "SoundCloud",
    "freshworks": "Freshworks",
    "freshdesk": "Freshdesk",
    "zoho": "Zoho",
    "starling": "Starling",
    "checkout": "Checkout.com",
    "outreach": "Outreach",
    "salesloft": "Salesloft",
    "monday": "Monday.com",
    "dbt": "dbt Labs",
    "cal": "Cal.com",
    "shop": "Shopify",
    "visa": "Visa",
    "adp": "ADP",
    "paychex": "Paychex",
    "sezzle": "Sezzle",
    "marqeta": "Marqeta",
    "tripadvisor": "Tripadvisor",
    "activision": "Activision",
    "take2": "Take-Two",
    "magento": "Magento",
    "inflection": "Inflection",
    "adept": "Adept",
}

GH_TOKENS_RAW = [
    # well-known first
    "airbnb",
    "stripe",
    "discord",
    "figma",
    "gitlab",
    "databricks",
    "snowflake",
    "cloudflare",
    "coinbase",
    "doordash",
    "lyft",
    "reddit",
    "dropbox",
    "zoom",
    "atlassian",
    "canva",
    "intercom",
    "gusto",
    "lattice",
    "plaid",
    "airtable",
    "asana",
    "webflow",
    "grafana",
    "mongodb",
    "hashicorp",
    "datadog",
    "okta",
    "hubspot",
    "spotify",
    "zendesk",
    "n26",
    "wise",
    "monzo",
    "adyen",
    "klarna",
    "nvidia",
    "tesla",
    "rivian",
    "huggingface",
    "mistral",
    "duolingo",
    "notion",
    "vercel",
    "openai",
    "anthropic",
    "twilio",
    "robinhood",
    "instacart",
    "uber",
    "pinterest",
    "box",
    "rippling",
    "mercury",
    "ramp",
    "brex",
    "linear",
    "cursor",
    "notionhq",
    "monday",
    "fivetran",
    "dbt",
    "hex",
    "hextechnologies",
    "hex-technologies",
    "elastic",
    "crowdstrike",
    "auth0",
    "sendgrid",
    "calcom",
    "cal",
    "supabase",
    "planetscale",
    "neon",
    "railway",
    "render",
    "flyio",
    "fly-io",
    "cloudkitchens",
    "gong",
    "outreach",
    "salesloft",
    "deel",
    "remotecom",
    "remote-com",
    "odoo",
    "sap",
    "siemens",
    "soundcloud",
    "freshworks",
    "zoho",
    "freshdesk",
    "shopifygh",
    "klaviyo",
    "revolut",
    "starling",
    "checkout",
    "afterpay",
    "block",
    "square",
    "cashapp",
    "tiktok",
    "bytedance",
    "amd",
    "intel",
    "arm",
    "qualcomm",
    "lucid",
    "cruise",
    "waymo",
    "anduril",
    "palantirgh",
    "scale",
    "scalesai",
    "stability",
    "midjourney",
    "perplexity",
    "characterai",
    "cohere",
    "adept",
    "inflection",
    "together",
    "fireworks",
    "groq",
    "cerebras",
    "sambanova",
    "lambda",
    "coreweave",
    "crusoe",
    "spacex",
    "blueorigin",
    "relativity",
    "rocketlab",
    "shieldai",
    "hadrian",
    "coursera",
    "udemy",
    "khanacademy",
    "khan-academy",
    "expedia",
    "bookingcom",
    "booking-com",
    "tripadvisor",
    "marriott",
    "hilton",
    "unity",
    "epicgames",
    "roblox",
    "twitch",
    "riotgames",
    "riot-games",
    "ea",
    "electronicarts",
    "activision",
    "take2",
    "service-now",
    "servicenow",
    "salesforce",
    "workday",
    "intuit",
    "adp",
    "paychex",
    "toast",
    "shop",
    "shopify",
    "woocommerce",
    "bigcommerce",
    "magento",
    "paypal",
    "visa",
    "mastercard",
    "amex",
    "capitalone",
    "sofi",
    "affirm",
    "sezzle",
    "marqeta",
]

LV_TOKENS_RAW = [
    "netflix",
    "palantir",
    "shopify",
    "mixpanel",
    "amplitude",
    "yelp",
    "quora",
    "eventbrite",
    "lever",
    "twilio",
    "sourceday",
    "segment",
    "fivetran",
    "box",
    "medium",
    "notion",
    "graviton",
    "gravitondata",
    "graviton-data",
    "gravitonhq",
    "reddit",
    "twitch",
    "kensho",
    "two-sigma",
    "twosigma",
    "jane-street",
    "janestreet",
    "citadel",
    "jumptrading",
    "hudson-river",
    "hrt",
    "optiver",
    "imc",
    "flowtraders",
    "drw",
    "sig",
    "susquehanna",
    "virtu",
    "tower-research",
    "de-shaw",
    "deshaw",
    "renaissance",
    "figma",
    "canva",
    "atlassian",
    "zendesk",
    "spotify",
    "wise",
    "revolut",
    "n26",
    "klarna",
    "adyen",
    "stripe",
    "coinbase",
    "kraken",
    "gemini",
    "robinhood",
    "sofi",
    "affirm",
    "toast",
    "toasttab",
    "toast-tab",
    "toastinc",
]


class MLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fed: list[str] = []

    def handle_data(self, d: str) -> None:
        self.fed.append(d)

    def get_data(self) -> str:
        return " ".join(self.fed)


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    s = MLStripper()
    try:
        s.feed(text)
        out = s.get_data()
    except Exception:
        out = re.sub(r"<[^>]+>", " ", text)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def short_desc(text: str, fallback: str = "") -> str:
    cleaned = strip_html(text or "")
    if not cleaned:
        cleaned = (fallback or "").strip()
    if len(cleaned) > 300:
        cleaned = cleaned[:297].rstrip() + "..."
    return cleaned


def title_company(token: str) -> str:
    key = token.lower().strip()
    if key in COMPANY_NAMES:
        return COMPANY_NAMES[key]
    return re.sub(r"[-_]+", " ", token).strip().title()


def uniq_tokens(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in raw:
        k = t.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            ts = float(value)
            if ts > 1e12:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).date()
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    # ISO / date
    try:
        if s.endswith("Z"):
            s2 = s[:-1] + "+00:00"
            return datetime.fromisoformat(s2).date()
        if "T" in s:
            return datetime.fromisoformat(s).date()
        return date.fromisoformat(s[:10])
    except Exception:
        pass
    # epoch as string
    if re.fullmatch(r"\d{10,13}", s):
        try:
            ts = float(s)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).date()
        except Exception:
            return None
    return None


def fmt_posted(value: Any, d: date | None) -> str | None:
    if value is None or value == "":
        return None
    if d is None:
        return None
    if isinstance(value, str) and "T" in value:
        return value
    return d.isoformat()


def date_keep(d: date | None) -> tuple[bool, bool]:
    """Return (keep, is_fallback). Missing date → keep."""
    if d is None:
        return True, False
    if AUG_START <= d < AUG_END:
        return True, False
    if FALLBACK_START <= d < AUG_START:
        return True, True
    return False, False


def is_remote_text(text: str) -> bool:
    if not text:
        return False
    return bool(REMOTE_RE.search(text))


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def infer_country_state_city(blob: str) -> tuple[str, str, str]:
    """Map free-text location to (country, state, city). Country '' if unknown."""
    raw = _norm_ws(blob)
    if not raw:
        return "", "", ""
    low = raw.lower()

    country = ""
    state = ""
    city = ""

    # Explicit country phrases
    country_patterns = [
        (r"\bunited states of america\b|\bunited states\b|\bu\.s\.a\.?\b|\bu\.s\.?\b|\busa\b", "USA"),
        (r"\bunited kingdom\b|\bgreat britain\b|\bengland\b|\bscotland\b|\bwales\b|\bnorthern ireland\b|\bu\.k\.?\b|\buk\b", "UK"),
        (r"\bnetherlands\b|\bthe netherlands\b|\bholland\b", "Netherlands"),
        (r"\bsingapore\b", "Singapore"),
        (r"\baustralia\b", "Australia"),
        (r"\bgermany\b|\bdeutschland\b", "Germany"),
        (r"\bireland\b", "Ireland"),
        (r"\bfrance\b", "France"),
        (r"\bcanada\b", "Canada"),
        (r"\bindia\b", "India"),
    ]
    for pat, name in country_patterns:
        if re.search(pat, low):
            country = name
            break

    # ISO-ish country tokens as standalone parts
    parts = [p.strip() for p in re.split(r"[,|/–—;-]+", raw) if p.strip()]
    low_parts = [p.lower() for p in parts]

    iso_map = {
        "us": "USA",
        "usa": "USA",
        "united states": "USA",
        "america": "USA",
        "in": "India",
        "ind": "India",
        "india": "India",
        "ca": None,  # ambiguous
        "can": "Canada",
        "canada": "Canada",
        "uk": "UK",
        "gb": "UK",
        "gbr": "UK",
        "au": "Australia",
        "aus": "Australia",
        "australia": "Australia",
        "de": None,  # ambiguous
        "deu": "Germany",
        "germany": "Germany",
        "nl": "Netherlands",
        "nld": "Netherlands",
        "netherlands": "Netherlands",
        "ie": "Ireland",
        "irl": "Ireland",
        "ireland": "Ireland",
        "sg": "Singapore",
        "sgp": "Singapore",
        "singapore": "Singapore",
        "fr": "France",
        "fra": "France",
        "france": "France",
    }

    # City from known list
    for p in low_parts:
        p2 = p.strip()
        if p2 in CITY_COUNTRY:
            if not city:
                city = p.title() if p2 not in ("nyc", "sf") else (
                    "New York" if p2 == "nyc" else "San Francisco"
                )
            if not country:
                country = CITY_COUNTRY[p2]
        else:
            # try first token of multiword? already split
            pass

    # Scan whole string for known cities if still missing
    if not city:
        # longest keys first
        for cname in sorted(CITY_COUNTRY.keys(), key=len, reverse=True):
            if re.search(rf"\b{re.escape(cname)}\b", low):
                city = (
                    "New York"
                    if cname == "nyc"
                    else "San Francisco"
                    if cname == "sf"
                    else cname.title()
                )
                if not country:
                    country = CITY_COUNTRY[cname]
                break

    # US "City, ST" pattern
    m = re.search(
        r"\b([A-Za-z .'-]+?),\s*([A-Z]{2})\b(?:\s*,\s*(?:USA|US|United States))?",
        raw,
    )
    if m:
        c_guess = m.group(1).strip()
        st = m.group(2).lower()
        c_low = c_guess.lower()
        if st in US_STATES:
            # Disambiguate IN / CA / DE
            if st == "in" and (c_low in INDIA_CITIES or country == "India"):
                country = "India"
                if not city:
                    city = c_guess
            elif st == "ca" and (c_low in CANADA_CITIES or country == "Canada"):
                country = "Canada"
                if not city:
                    city = c_guess
            elif st == "de" and (c_low in GERMANY_CITIES or country == "Germany"):
                country = "Germany"
                if not city:
                    city = c_guess
            else:
                # treat as US state
                if country in ("", "USA"):
                    country = "USA"
                    state = US_STATES[st]
                    if not city:
                        city = c_guess

    # Full US state name
    if not state and (country in ("", "USA")):
        for p in low_parts:
            if p in US_STATE_NAMES:
                state = US_STATE_NAMES[p]
                if not country:
                    country = "USA"

    # Trailing ISO codes
    if not country:
        for p in reversed(low_parts):
            mapped = iso_map.get(p)
            if mapped:
                country = mapped
                break
            if p == "ca":
                # California vs Canada: if a US city/state already, USA
                if state or (city.lower() not in CANADA_CITIES and city):
                    # if city looks US or unknown with CA → USA if US city else Canada if canada city
                    if city.lower() in CANADA_CITIES:
                        country = "Canada"
                    else:
                        country = "USA"
                        if not state:
                            state = "California"
                else:
                    country = "USA"
                    if not state:
                        state = "California"
                break
            if p == "de":
                if city.lower() in GERMANY_CITIES:
                    country = "Germany"
                else:
                    country = "USA"
                    if not state:
                        state = "Delaware"
                break

    # America as USA (avoid "American Samoa" etc. already handled)
    if not country and re.search(r"\bamerica\b", low) and "south america" not in low:
        country = "USA"

    # Normalize city title
    if city:
        # fix accents-ish title
        if city.lower() == "montréal":
            city = "Montreal"
        elif city.lower() == "münchen":
            city = "Munich"
        elif city.lower() == "köln":
            city = "Cologne"

    if country and country not in TARGET_COUNTRIES:
        country = ""

    return country, state, city


def extract_gh_location(job: dict) -> tuple[str, str, str, bool]:
    bits: list[str] = []
    loc = job.get("location") or {}
    if isinstance(loc, dict):
        if loc.get("name"):
            bits.append(str(loc["name"]))
    elif isinstance(loc, str):
        bits.append(loc)

    offices = job.get("offices") or []
    office_remote = False
    if isinstance(offices, list):
        for off in offices:
            if not isinstance(off, dict):
                continue
            name = str(off.get("name") or "")
            if name.strip().lower() == "remote" or is_remote_text(name):
                office_remote = True
            bits.append(name)
            if off.get("location"):
                bits.append(str(off["location"]))
            # greenhouse sometimes nests country
            for k in ("country", "country_id"):
                if off.get(k) and not str(off.get(k)).isdigit():
                    bits.append(str(off[k]))

    blob = " | ".join(b for b in bits if b)
    remote = office_remote or is_remote_text(blob)
    country, state, city = infer_country_state_city(blob)
    return country, state, city, remote


def extract_lv_location(job: dict) -> tuple[str, str, str, bool]:
    cats = job.get("categories") or {}
    bits: list[str] = []
    if isinstance(cats, dict):
        for k in ("location", "commitment", "team", "department"):
            if cats.get(k):
                bits.append(str(cats[k]))
    if job.get("country"):
        bits.append(str(job["country"]))
    # workplaceType sometimes present
    if job.get("workplaceType"):
        bits.append(str(job["workplaceType"]))
    blob = " | ".join(b for b in bits if b)
    remote = is_remote_text(blob)
    # also description snippet for remote? skip — list fields only
    country, state, city = infer_country_state_city(blob)
    return country, state, city, remote


def should_keep_geo(country: str, remote: bool) -> bool:
    if remote:
        return True
    return country in TARGET_COUNTRIES


def http_get(url: str) -> tuple[int, Any, str]:
    """Return (status, json_or_none, err). Retry once on 429."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200) or 200
            try:
                return status, json.loads(body.decode("utf-8", errors="replace")), ""
            except json.JSONDecodeError as e:
                return status, None, f"json:{e}"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(RETRY_429_WAIT)
            try:
                req2 = urllib.request.Request(
                    url, headers={"User-Agent": UA, "Accept": "application/json"}
                )
                with urllib.request.urlopen(req2, timeout=TIMEOUT) as resp:
                    body = resp.read()
                    status = getattr(resp, "status", 200) or 200
                    try:
                        return status, json.loads(body.decode("utf-8", errors="replace")), ""
                    except json.JSONDecodeError as je:
                        return status, None, f"json:{je}"
            except urllib.error.HTTPError as e2:
                return e2.code, None, str(e2.reason or e2)
            except Exception as e2:
                return 0, None, str(e2)
        return e.code, None, str(e.reason or e)
    except Exception as e:
        return 0, None, str(e)


def log_line(fh, msg: str) -> None:
    fh.write(msg + "\n")
    fh.flush()
    print(msg, flush=True)


def append_jsonl(path: Path, rec: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def normalize_gh(token: str, job: dict) -> dict | None:
    jid = job.get("id")
    if jid is None:
        return None
    title = str(job.get("title") or "").strip()
    url = str(job.get("absolute_url") or "").strip()
    if not url:
        return None
    country, state, city, remote = extract_gh_location(job)
    raw_date = job.get("first_published") or job.get("firstPublished") or job.get("updated_at")
    # Prefer first_published for posted_at; if only updated_at, still use it
    d = parse_date(job.get("first_published") or job.get("firstPublished"))
    if d is None:
        d = parse_date(job.get("updated_at"))
        raw_date = job.get("updated_at") if d else None
    else:
        raw_date = job.get("first_published") or job.get("firstPublished")
    keep, fallback = date_keep(d)
    if not keep:
        return None
    if not should_keep_geo(country, remote):
        return None
    desc_src = (
        job.get("content")
        or job.get("description")
        or ""
    )
    api_co = str(job.get("company_name") or "").strip()
    rec = {
        "id": f"greenhouse:{token}:{jid}",
        "title": title,
        "company": api_co if api_co else title_company(token),
        "country": country,
        "state": state,
        "city": city,
        "remote": bool(remote),
        "url": url,
        "posted_at": fmt_posted(raw_date, d),
        "source": "greenhouse",
        "description": short_desc(str(desc_src), fallback=title),
    }
    rec["_fallback"] = fallback
    return rec


def normalize_lv(token: str, job: dict) -> dict | None:
    jid = job.get("id")
    if jid is None:
        return None
    title = str(job.get("text") or job.get("title") or "").strip()
    url = str(job.get("hostedUrl") or job.get("applyUrl") or "").strip()
    if not url:
        return None
    country, state, city, remote = extract_lv_location(job)
    raw_date = job.get("createdAt")
    d = parse_date(raw_date)
    keep, fallback = date_keep(d)
    if not keep:
        return None
    if not should_keep_geo(country, remote):
        return None
    desc_src = job.get("descriptionPlain") or job.get("description") or ""
    posted = None
    if d is not None:
        posted = d.isoformat()
    rec = {
        "id": f"lever:{token}:{jid}",
        "title": title,
        "company": title_company(token),
        "country": country,
        "state": state,
        "city": city,
        "remote": bool(remote),
        "url": url,
        "posted_at": posted,
        "source": "lever",
        "description": short_desc(str(desc_src), fallback=title),
    }
    rec["_fallback"] = fallback
    return rec


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_DIR.mkdir(parents=True, exist_ok=True)
    for p in (GH_OUT, LV_OUT, LOG_PATH):
        if p.exists():
            p.unlink()

    gh_tokens = uniq_tokens(GH_TOKENS_RAW)
    lv_tokens = uniq_tokens(LV_TOKENS_RAW)

    stats = {
        "gh_attempted": 0,
        "gh_ok": 0,
        "gh_404": 0,
        "gh_other": 0,
        "lv_attempted": 0,
        "lv_ok": 0,
        "lv_404": 0,
        "lv_other": 0,
        "gh_raw_jobs": 0,
        "lv_raw_jobs": 0,
        "gh_written": 0,
        "lv_written": 0,
        "gh_aug": 0,
        "gh_fallback": 0,
        "gh_null_date": 0,
        "lv_aug": 0,
        "lv_fallback": 0,
        "lv_null_date": 0,
    }
    boards_with_jobs: list[str] = []
    boards_with_kept: list[str] = []
    sample_jobs: list[dict] = []
    saved_sample = False
    start = time.monotonic()
    timed_out = False

    seen_gh_urls: set[str] = set()
    seen_lv_urls: set[str] = set()

    with LOG_PATH.open("w", encoding="utf-8") as log:
        log_line(log, f"# ATS pull start utc={datetime.now(timezone.utc).isoformat()}")
        log_line(log, f"# greenhouse_tokens={len(gh_tokens)} lever_tokens={len(lv_tokens)} budget={TIME_BUDGET_SEC}s")

        def budget_ok() -> bool:
            return (time.monotonic() - start) < TIME_BUDGET_SEC

        def polite() -> None:
            time.sleep(random.uniform(DELAY_LO, DELAY_HI))

        # Greenhouse
        for token in gh_tokens:
            if not budget_ok():
                timed_out = True
                log_line(log, f"# TIME BOX reached before remaining greenhouse tokens (at {token})")
                break
            stats["gh_attempted"] += 1
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
            status, data, err = http_get(url)
            polite()
            if status == 404:
                stats["gh_404"] += 1
                log_line(log, f"greenhouse\t{token}\t404\t0\t{err}")
                continue
            if status != 200 or data is None:
                stats["gh_other"] += 1
                log_line(log, f"greenhouse\t{token}\t{status}\t0\t{err}")
                continue
            jobs = data.get("jobs") if isinstance(data, dict) else None
            if jobs is None:
                stats["gh_other"] += 1
                log_line(log, f"greenhouse\t{token}\t{status}\t0\tno-jobs-key")
                continue
            stats["gh_ok"] += 1
            n_raw = len(jobs)
            stats["gh_raw_jobs"] += n_raw
            if n_raw > 0:
                boards_with_jobs.append(f"greenhouse:{token}")
            if not saved_sample and n_raw > 0:
                try:
                    GH_SAMPLE.write_text(
                        json.dumps({"board": token, "jobs": jobs[:3]}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    saved_sample = True
                except Exception:
                    pass
            kept = 0
            for job in jobs:
                rec = normalize_gh(token, job)
                if rec is None:
                    continue
                u = rec["url"]
                if u in seen_gh_urls:
                    continue
                seen_gh_urls.add(u)
                fb = rec.pop("_fallback", False)
                if rec["posted_at"] is None:
                    stats["gh_null_date"] += 1
                elif fb:
                    stats["gh_fallback"] += 1
                else:
                    stats["gh_aug"] += 1
                append_jsonl(GH_OUT, rec)
                stats["gh_written"] += 1
                kept += 1
                if len(sample_jobs) < 3:
                    sample_jobs.append(rec)
            if kept:
                boards_with_kept.append(f"greenhouse:{token}")
            log_line(log, f"greenhouse\t{token}\t{status}\t{n_raw}\tkept={kept}")

        # Lever
        for token in lv_tokens:
            if not budget_ok():
                timed_out = True
                log_line(log, f"# TIME BOX reached before remaining lever tokens (at {token})")
                break
            stats["lv_attempted"] += 1
            url = f"https://api.lever.co/v0/postings/{token}?mode=json"
            status, data, err = http_get(url)
            polite()
            if status == 404:
                stats["lv_404"] += 1
                log_line(log, f"lever\t{token}\t404\t0\t{err}")
                continue
            if status != 200 or data is None:
                stats["lv_other"] += 1
                log_line(log, f"lever\t{token}\t{status}\t0\t{err}")
                continue
            if not isinstance(data, list):
                stats["lv_other"] += 1
                log_line(log, f"lever\t{token}\t{status}\t0\tnot-a-list")
                continue
            stats["lv_ok"] += 1
            n_raw = len(data)
            stats["lv_raw_jobs"] += n_raw
            if n_raw > 0:
                boards_with_jobs.append(f"lever:{token}")
            kept = 0
            for job in data:
                rec = normalize_lv(token, job)
                if rec is None:
                    continue
                u = rec["url"]
                if u in seen_lv_urls:
                    continue
                seen_lv_urls.add(u)
                fb = rec.pop("_fallback", False)
                if rec["posted_at"] is None:
                    stats["lv_null_date"] += 1
                elif fb:
                    stats["lv_fallback"] += 1
                else:
                    stats["lv_aug"] += 1
                append_jsonl(LV_OUT, rec)
                stats["lv_written"] += 1
                kept += 1
                if len(sample_jobs) < 3:
                    sample_jobs.append(rec)
            if kept:
                boards_with_kept.append(f"lever:{token}")
            log_line(log, f"lever\t{token}\t{status}\t{n_raw}\tkept={kept}")

        elapsed = time.monotonic() - start
        summary = {
            "elapsed_sec": round(elapsed, 1),
            "timed_out": timed_out,
            "stats": stats,
            "boards_with_raw_jobs": boards_with_jobs,
            "boards_with_kept_jobs": boards_with_kept,
        }
        (RAW_DIR / "ats_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        log_line(log, f"# done elapsed={elapsed:.1f}s timed_out={timed_out}")
        log_line(log, f"# stats {json.dumps(stats)}")
        log_line(log, f"# boards_with_jobs {json.dumps(boards_with_jobs)}")

    print("SUMMARY", json.dumps(stats, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

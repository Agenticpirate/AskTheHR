#!/usr/bin/env python3
"""Normalize all raw dumps + existing jsonl and overwrite site ingest. No API fetches."""
from __future__ import annotations
import html, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

RAW = Path("/workspace/jobs/raw")
OUT = Path("/workspace/jobs/normalized")
COMBINED = Path("/workspace/jobs/remote-aug2026.jsonl")
SUMMARY = Path("/workspace/jobs/summary.json")
TARGET = ["USA","India","Canada","UK","Australia","Germany","Netherlands","Ireland","Singapore","France"]
TARGET_SET = set(TARGET)
REMOTE_BOARDS = {
    "remoteok","remotive","jobicy","weworkremotely","himalayas",
    "workingnomads","remotejobsorg","remotefirstjobs",
}
REMOTE_RE = re.compile(
    r"\b(remote|worldwide|distributed|work[\s-]?from[\s-]?home|wfh|workfromhome|anywhere|remoto|fully[\s-]?remote)\b",
    re.I,
)
HYBRID_RE = re.compile(r"\bhybrid\b", re.I)
TRACKING = {"fbclid","gclid","gclsrc","dclid","msclkid","mc_cid","mc_eid","_ga","_gl","igshid","spm","ref","ref_src","referrer"}
SKIP_EXACT = {"_normalize_summary.json","ats_boards.log","paginate_log.txt","_jobdata_pages.log","ats_summary.json"}
SKIP_SUFF = (".html",".log",".txt",".md")
KEYS = ["id","title","company","country","state","city","remote","url","posted_at","source","description"]

ALIASES = [
    ("united states of america","USA"),("united states","USA"),("u.s.a.","USA"),("u.s.","USA"),
    ("america","USA"),("united kingdom","UK"),("great britain","UK"),("northern ireland","UK"),
    ("england","UK"),("scotland","UK"),("wales","UK"),("britain","UK"),("u.k.","UK"),
    ("the netherlands","Netherlands"),("netherlands","Netherlands"),("holland","Netherlands"),
    ("deutschland","Germany"),("germany","Germany"),("republic of ireland","Ireland"),
    ("ireland","Ireland"),("singapore","Singapore"),("australia","Australia"),
    ("canada","Canada"),("france","France"),("india","India"),("bharat","India"),
]
ISO = {"us":"USA","usa":"USA","uk":"UK","gb":"UK","gbr":"UK","in":"India","ind":"India",
       "ca":"Canada","can":"Canada","au":"Australia","aus":"Australia","de":"Germany","deu":"Germany",
       "nl":"Netherlands","nld":"Netherlands","ie":"Ireland","irl":"Ireland","sg":"Singapore",
       "sgp":"Singapore","fr":"France","fra":"France"}
US_ABBR = {"al":"Alabama","ak":"Alaska","az":"Arizona","ar":"Arkansas","ca":"California","co":"Colorado",
    "ct":"Connecticut","de":"Delaware","fl":"Florida","ga":"Georgia","hi":"Hawaii","id":"Idaho",
    "il":"Illinois","ia":"Iowa","ks":"Kansas","ky":"Kentucky","la":"Louisiana",
    "me":"Maine","md":"Maryland","ma":"Massachusetts","mi":"Michigan","mn":"Minnesota","ms":"Mississippi",
    "mo":"Missouri","mt":"Montana","ne":"Nebraska","nv":"Nevada","nh":"New Hampshire","nj":"New Jersey",
    "nm":"New Mexico","ny":"New York","nc":"North Carolina","nd":"North Dakota","oh":"Ohio",
    "ok":"Oklahoma","or":"Oregon","pa":"Pennsylvania","ri":"Rhode Island","sc":"South Carolina",
    "sd":"South Dakota","tn":"Tennessee","tx":"Texas","ut":"Utah","vt":"Vermont","va":"Virginia",
    "wa":"Washington","wv":"West Virginia","wi":"Wisconsin","wy":"Wyoming","dc":"District of Columbia"}
US_NAMES = {v.lower(): v for v in US_ABBR.values()}
US_NAMES.update({"washington dc":"District of Columbia","washington d.c.":"District of Columbia","d.c.":"District of Columbia"})
CA_PROV = {"ontario":"Ontario","quebec":"Quebec","québec":"Quebec","british columbia":"British Columbia",
    "alberta":"Alberta","manitoba":"Manitoba","saskatchewan":"Saskatchewan","nova scotia":"Nova Scotia",
    "new brunswick":"New Brunswick","newfoundland":"Newfoundland and Labrador","newfoundland and labrador":"Newfoundland and Labrador",
    "bc":"British Columbia","on":"Ontario","ab":"Alberta","qc":"Quebec"}

def _cities(country, items):
    for k, st, disp in items:
        CITY[k] = (country, st, disp)
CITY = {}
_cities("India",[
    ("bengaluru","Karnataka","Bengaluru"),("bangalore","Karnataka","Bengaluru"),
    ("hyderabad","Telangana","Hyderabad"),("mumbai","Maharashtra","Mumbai"),
    ("delhi","Delhi","Delhi"),("new delhi","Delhi","New Delhi"),
    ("pune","Maharashtra","Pune"),("chennai","Tamil Nadu","Chennai"),
    ("gurgaon","Haryana","Gurugram"),("gurugram","Haryana","Gurugram"),
    ("noida","Uttar Pradesh","Noida"),("kolkata","West Bengal","Kolkata"),
    ("ahmedabad","Gujarat","Ahmedabad"),("chandigarh","Chandigarh","Chandigarh"),
    ("mohali","Punjab","Mohali"),
])
_cities("Canada",[
    ("toronto","Ontario","Toronto"),("vancouver","British Columbia","Vancouver"),
    ("montreal","Quebec","Montreal"),("montréal","Quebec","Montreal"),
    ("ottawa","Ontario","Ottawa"),("calgary","Alberta","Calgary"),
    ("edmonton","Alberta","Edmonton"),("waterloo","Ontario","Waterloo"),
    ("mississauga","Ontario","Mississauga"),("winnipeg","Manitoba","Winnipeg"),
    ("moncton","New Brunswick","Moncton"),
])
_cities("UK",[
    ("london","England","London"),("manchester","North West","Manchester"),
    ("edinburgh","Scotland","Edinburgh"),("belfast","Northern Ireland","Belfast"),
    ("birmingham","England","Birmingham"),("bristol","South West","Bristol"),
    ("leeds","Yorkshire and the Humber","Leeds"),("sheffield","Yorkshire and the Humber","Sheffield"),
    ("glasgow","Scotland","Glasgow"),("cambridge","East of England","Cambridge"),
    ("oxford","England","Oxford"),("cardiff","Wales","Cardiff"),
])
_cities("Australia",[
    ("sydney","New South Wales","Sydney"),("melbourne","Victoria","Melbourne"),
    ("brisbane","Queensland","Brisbane"),("perth","Western Australia","Perth"),
    ("canberra","Australian Capital Territory","Canberra"),("adelaide","South Australia","Adelaide"),
])
_cities("Germany",[
    ("berlin","Berlin","Berlin"),("munich","Bavaria","Munich"),("münchen","Bavaria","Munich"),
    ("muenchen","Bavaria","Munich"),("hamburg","Hamburg","Hamburg"),("frankfurt","Hesse","Frankfurt"),
    ("cologne","North Rhine-Westphalia","Cologne"),("köln","North Rhine-Westphalia","Cologne"),
    ("koeln","North Rhine-Westphalia","Cologne"),("stuttgart","Baden-Württemberg","Stuttgart"),
    ("düsseldorf","North Rhine-Westphalia","Düsseldorf"),("dusseldorf","North Rhine-Westphalia","Düsseldorf"),
    ("leipzig","Saxony","Leipzig"),("hannover","Lower Saxony","Hannover"),("nürnberg","Bavaria","Nuremberg"),
    ("nuremberg","Bavaria","Nuremberg"),("bremen","Bremen","Bremen"),("dortmund","North Rhine-Westphalia","Dortmund"),
    ("aachen","North Rhine-Westphalia","Aachen"),("heidelberg","Baden-Württemberg","Heidelberg"),
    ("karlsruhe","Baden-Württemberg","Karlsruhe"),("dresden","Saxony","Dresden"),("bonn","North Rhine-Westphalia","Bonn"),
])
_cities("Netherlands",[
    ("amsterdam","North Holland","Amsterdam"),("rotterdam","South Holland","Rotterdam"),
    ("utrecht","Utrecht","Utrecht"),("eindhoven","North Brabant","Eindhoven"),
    ("the hague","South Holland","The Hague"),("den haag","South Holland","The Hague"),
])
_cities("Ireland",[
    ("dublin","Dublin","Dublin"),("cork","Cork","Cork"),
    ("galway","Galway","Galway"),("limerick","Limerick","Limerick"),
])
_cities("Singapore",[("singapore","Singapore","Singapore")])
_cities("France",[
    ("paris","Île-de-France","Paris"),("lyon","Auvergne-Rhône-Alpes","Lyon"),
    ("grenoble","Auvergne-Rhône-Alpes","Grenoble"),
    ("toulouse","Occitanie","Toulouse"),("montpellier","Occitanie","Montpellier"),
    ("nantes","Pays de la Loire","Nantes"),("rennes","Bretagne","Rennes"),
    ("bordeaux","Nouvelle-Aquitaine","Bordeaux"),
    ("marseille","Provence-Alpes-Côte d'Azur","Marseille"),
    ("nice","Provence-Alpes-Côte d'Azur","Nice"),
    ("lille","Hauts-de-France","Lille"),("strasbourg","Grand Est","Strasbourg"),
])
_cities("USA",[
    ("new york","New York","New York"),("new york city","New York","New York"),
    ("san francisco","California","San Francisco"),
    ("los angeles","California","Los Angeles"),("seattle","Washington","Seattle"),
    ("austin","Texas","Austin"),("boston","Massachusetts","Boston"),
    ("chicago","Illinois","Chicago"),("denver","Colorado","Denver"),
    ("atlanta","Georgia","Atlanta"),("miami","Florida","Miami"),
    ("dallas","Texas","Dallas"),("houston","Texas","Houston"),
    ("palo alto","California","Palo Alto"),("mountain view","California","Mountain View"),
    ("washington dc","District of Columbia","Washington"),
    ("portland","Oregon","Portland"),("san diego","California","San Diego"),
    ("san jose","California","San Jose"),("redmond","Washington","Redmond"),
    ("bellevue","Washington","Bellevue"),
])
NON_US = {k for k,v in CITY.items() if v[0] != "USA"}

# Extra city -> state fill (country-aware), applied when state is empty
CITY_STATE = {}
for key,(country,state,disp) in CITY.items():
    if state:
        CITY_STATE[(country, disp.lower())] = state
        CITY_STATE[(country, key)] = state

class _Strip(HTMLParser):
    def __init__(self):
        super().__init__(); self.p=[]
    def handle_data(self, d): self.p.append(d)
    def handle_entityref(self, n): self.p.append(html.unescape(f"&{n};"))
    def handle_charref(self, n): self.p.append(html.unescape(f"&#{n};"))

def strip_html(text):
    if text is None: return ""
    s = html.unescape(str(text))
    if "â" in s or "Ã" in s:
        try: s = s.encode("latin-1").decode("utf-8")
        except Exception: pass
    st = _Strip()
    try:
        st.feed(s); st.close(); s = "".join(st.p)
    except Exception:
        s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0"," ")
    return re.sub(r"\s+", " ", s).strip()

def short_desc(text, n=300):
    s = strip_html(text)
    return s if len(s)<=n else s[:n].rstrip()

def truthy(v):
    if v is True: return True
    if v in (False, None): return False
    if isinstance(v,(int,float)): return bool(v)
    return str(v).strip().lower() in {"1","true","yes","y","remote"}

def normalize_url(url):
    if not url: return ""
    u = str(url).strip()
    if not u or u.lower() in {"none","null","n/a"}: return ""
    if u.startswith("//"): u = "https:"+u
    p = urlparse(u)
    host = p.netloc.lower()
    if not host: return u.rstrip("/")
    q=[]
    for k,v in parse_qsl(p.query, keep_blank_values=True):
        kl=k.lower()
        if kl.startswith("utm_") or kl in TRACKING: continue
        q.append((k,v))
    return urlunparse(((p.scheme or "https").lower(), host, p.path.rstrip("/"), "", urlencode(q, doseq=True), ""))

def parse_posted_at(value):
    if value is None or value == "": return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if value.tzinfo else value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, (int, float)):
        n = int(value)
        if n <= 0: return None
        if n > 10**12: n //= 1000
        if n < 10**8: return None
        try: return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception: return None
    s = str(value).strip()
    if not s or s.lower() in {"none","null","n/a"}: return None
    if re.fullmatch(r"-?\d+(\.0+)?", s):
        try: return parse_posted_at(int(float(s)))
        except Exception: return None
    if re.match(r"^[A-Za-z]{3},", s):
        try:
            dt = parsedate_to_datetime(s)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt.tzinfo else dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception: pass
    try:
        dt = datetime.fromisoformat(s.replace("Z","+00:00"))
        if dt.tzinfo: return dt.isoformat()
        return dt.strftime("%Y-%m-%dT%H:%M:%S") if ("T" in s or " " in s) else dt.strftime("%Y-%m-%d")
    except ValueError: pass
    if re.search(r"\d{4}", s): return s
    return None

def looks_remote(blobs, source, explicit=None):
    if source in REMOTE_BOARDS: return True
    if truthy(explicit): return True
    if isinstance(explicit, str) and explicit.strip().lower() in {"remote","hybrid"}: return True
    parts=[]
    for b in blobs:
        if b is None: continue
        if isinstance(b,(list,tuple,set)): parts.extend(str(x) for x in b if x is not None)
        else: parts.append(str(b))
    text=" ".join(parts)
    return bool(REMOTE_RE.search(text) or HYBRID_RE.search(text))

def find_alias(text):
    if not text: return None
    low=text.lower()
    for alias,canon in ALIASES:
        idx=0
        while True:
            pos=low.find(alias, idx)
            if pos<0: break
            b=low[pos-1] if pos else " "
            a=low[pos+len(alias)] if pos+len(alias)<len(low) else " "
            if not b.isalnum() and not a.isalnum(): return canon
            idx=pos+len(alias)
    return None

def parse_location(*raw_parts):
    chunks=[]
    for p in raw_parts:
        if p is None: continue
        if isinstance(p,(list,tuple,set)):
            for x in p:
                if isinstance(x, dict):
                    n=x.get("name") or x.get("asciiname") or x.get("code") or x.get("location") or ""
                    if n: chunks.append(str(n))
                elif x: chunks.append(str(x))
        elif isinstance(p, dict):
            n=p.get("name") or p.get("asciiname") or p.get("code") or p.get("location") or ""
            if n: chunks.append(str(n))
            pa=p.get("postalAddress") if isinstance(p.get("postalAddress"), dict) else None
            if pa:
                for k in ("addressLocality","addressRegion","addressCountry"):
                    if pa.get(k): chunks.append(str(pa[k]))
        else:
            s=str(p).strip()
            if s and s.lower() not in {"none","null","n/a","hybrid","in-office","onsite","on-site"}:
                chunks.append(s)
    if not chunks: return "","",""
    text=" | ".join(re.sub(r"\s+"," ",html.unescape(c)).strip(" ,;|/") for c in chunks if c)
    tokens=[t.strip() for t in re.split(r"[,;/|]+", text) if t.strip()]
    extra=[]
    for t in tokens:
        extra.extend(x.strip() for x in re.split(r"\s+-\s+|-\s+", t) if x.strip())
    all_toks=tokens+extra
    country=state=city=""
    for t in tokens:
        m=re.match(r"^(.+?),\s*([A-Za-z]{2})\.?$", t.strip())
        if not m: continue
        cname,st=m.group(1).strip(), m.group(2).lower()
        if st in US_ABBR:
            if cname.lower() in NON_US:
                country,state,city=CITY[cname.lower()]
            else:
                country,state,city="USA",US_ABBR[st],cname
                break
    if not country:
        for t in all_toks:
            tl=re.sub(r"^(remote|hybrid|onsite|on-site|in-office)\s*[-:]?\s*","",t.lower()).strip()
            if tl in CITY:
                country,state,city=CITY[tl]; break
    if not country:
        country = find_alias(text) or ""
    if not country:
        for t in all_toks:
            tl=re.sub(r"^(remote|hybrid)\s*","",t.lower().strip().rstrip("."))
            if tl in ISO: country=ISO[tl]; break
    if not country:
        for t in all_toks:
            tl=t.lower().strip()
            if tl in CA_PROV: country,state="Canada",CA_PROV[tl]; break
            if tl in US_NAMES: country,state="USA",US_NAMES[tl]; break
    if not country:
        for t in all_toks:
            m=re.match(r"^(us|usa|uk|gb|ca|au|de|nl|ie|sg|fr|in)[-\s]+(.+)$", t.strip(), re.I)
            if m:
                country=ISO.get(m.group(1).lower(),"")
                rest=m.group(2).strip()
                if rest.lower() in CITY: country,state,city=CITY[rest.lower()]
                elif rest.lower() not in {"remote","hybrid","anywhere"}: city=rest
                break
            m=re.match(r"^(.+?)[-\s]+(us|usa|uk|gb|ca|au|de|nl|ie|sg|fr|in)$", t.strip(), re.I)
            if m:
                left,code=m.group(1).strip(), m.group(2).lower()
                if left.lower() in CITY: country,state,city=CITY[left.lower()]
                else:
                    country=ISO.get(code,"")
                    if left.lower() not in {"remote","hybrid","anywhere"}: city=left
                break
    if not city:
        skip={"remote","hybrid","onsite","on-site","in-office","worldwide","anywhere","global","flexible","n/a","na","unspecified","emea","apac","latam","americas","europe","asia","africa"}
        skip |= {c.lower() for c in TARGET} | {a for a,_ in ALIASES} | set(ISO) | set(US_ABBR) | set(CA_PROV)
        for t in tokens:
            tl=re.sub(r"^(remote|hybrid|onsite|on-site)\s*[-:]?\s*","",t.lower()).strip()
            if not tl or tl in skip or find_alias(tl): continue
            if tl in CITY:
                c2,s2,ci=CITY[tl]
                if not country: country,state=c2,s2
                city=ci; break
            city=t.strip(); break
    if country and country not in TARGET_SET: country=""
    if country and city and not state:
        state = CITY_STATE.get((country, city.lower()), "") or CITY_STATE.get((country, city.lower().strip()), "")
    return country, state, city

def fill_state(country, state, city):
    if state or not country or not city:
        return state or ""
    return CITY_STATE.get((country, city.lower().strip()), "") or state or ""

def record(*, id_, title, company, country, state, city, remote, url, posted_at, source, description):
    title, company = strip_html(title), strip_html(company)
    url = normalize_url(url)
    if not url or not title: return None
    if country not in TARGET_SET: country=""
    if not remote and country not in TARGET_SET: return None
    if source == "arbeitnow" and not remote: return None
    state = fill_state(country, state or "", city or "")
    return {"id":str(id_),"title":title,"company":company,"country":country,"state":state or "","city":city or "",
            "remote":bool(remote),"url":url,"posted_at":posted_at,"source":source,"description":description or ""}

def company_from_url(url, fallback=""):
    if not url: return fallback
    p=urlparse(url); parts=[x for x in p.path.split("/") if x]; host=p.netloc.lower()
    if ("greenhouse.io" in host or "lever.co" in host or "ashbyhq.com" in host) and parts:
        return parts[0]
    return fallback

def slug_company(name):
    return re.sub(r"[^a-z0-9]+","",(name or "").lower())

def is_error_payload(data, head):
    h=head.lstrip().lower()
    if (h.startswith("<!doctype") or h.startswith("<html")) and "<rss" not in h[:500]:
        return "html page, not a job dump"
    if isinstance(data, str) and data.lower().startswith("http error"):
        return "http error body"
    if isinstance(data, dict):
        if data.get("success") is False and not data.get("jobs") and not data.get("data"):
            return f"api error: {data.get('error') or data.get('message') or 'success=false'}"
        if data.get("status") in (401,403,404) or data.get("statusCode") in (401,403,404):
            if not data.get("jobs") and not data.get("results") and not data.get("data"):
                return f"http error payload status={data.get('status') or data.get('statusCode')}"
        if data.get("error") and not any(data.get(k) for k in ("jobs","data","results","items")):
            err=str(data.get("error"))
            if "not found" in err.lower() or data.get("ok") is False:
                return f"error payload: {err[:120]}"
        if data.get("title")=="Unauthorized" and data.get("status")==401:
            return "unauthorized (401)"
        if data.get("ok") is False and not data.get("jobs"):
            return f"ok=false: {data.get('error') or ''}"[:120]
    return None

def load_json_file(path):
    try: raw=path.read_text(encoding="utf-8", errors="replace")
    except OSError as e: return None, f"read error: {e}"
    if not raw.strip(): return None, "empty file"
    if raw.strip().lower().startswith("http error"):
        return None, "http error body"
    try: data=json.loads(raw)
    except json.JSONDecodeError as e: return raw, f"not json: {e}"
    reason=is_error_payload(data, raw[:400])
    return (data, reason) if reason else (data, None)

def extract_jobs(data):
    if isinstance(data, list): return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ("jobs","data","results","items","jobPostings","positions"):
            v=data.get(k)
            if isinstance(v, list): return [x for x in v if isinstance(x, dict)]
    return []

def detect_schema(job):
    k=set(job)
    if "position" in k and ("apply_url" in k or "epoch" in k): return "remoteok"
    if "candidate_required_location" in k: return "remotive"
    if "jobTitle" in k and ("jobGeo" in k or "jobExcerpt" in k): return "jobicy"
    if "applicationLink" in k or "locationRestrictions" in k: return "himalayas"
    if "absolute_url" in k and ("first_published" in k or "internal_job_id" in k): return "greenhouse"
    if "hostedUrl" in k and "text" in k: return "lever"
    if "contents" in k and "refs" in k and "publication_date" in k: return "themuse"
    if "has_remote" in k and ("application_url" in k or "countries" in k): return "jobdata"
    if "slug" in k and "company_name" in k and "created_at" in k: return "arbeitnow"
    if "pub_date" in k and "company_name" in k and "url" in k: return "workingnomads"
    if "isRemote" in k and ("jobUrl" in k or "applyUrl" in k): return "ashby"
    if "jobPostingId" in k or ("applyUrl" in k and "departmentName" in k): return "ashby"
    if "apply_url" in k and "salary_text" in k and "posted_at" in k: return "remotejobsorg"
    if "published_at" in k and "company_name" in k and "locations" in k and "seniority" in k: return "remotefirstjobs"
    if "uuid" in k and "advertiser" in k: return "mcf"
    if "metadata" in k and "jobDetails" in k: return "mcf"
    return None

def source_from_name(name):
    n=name.lower()
    pairs=(("remoteok","remoteok"),("remotive","remotive"),("jobicy","jobicy"),
           ("arbeitnow","arbeitnow"),("himalayas","himalayas"),("wwr","weworkremotely"),
           ("weworkremotely","weworkremotely"),("themuse","themuse"),("gh_","greenhouse"),
           ("greenhouse","greenhouse"),("lever","lever"),("ashby","ashby"),
           ("jobdata","jobdata"),("workingnomads","workingnomads"),
           ("remotejobsorg","remotejobsorg"),("rfj_","remotefirstjobs"),
           ("remotefirst","remotefirstjobs"),("mcf_","mcf"),("workable_","workable"))
    for pref,src in pairs:
        if n.startswith(pref): return src
    if re.match(r"page\d+", n): return "arbeitnow"
    return None

def conv_remoteok(j, source, hint=""):
    if j.get("legal") or not j.get("position"): return None
    loc, title, tags = j.get("location") or "", j.get("position") or "", j.get("tags") or []
    c,st,ci=parse_location(loc)
    return record(id_=f"remoteok:{j.get('id') or j.get('slug')}", title=title, company=j.get("company") or "",
        country=c,state=st,city=ci, remote=looks_remote([loc,title,tags],source),
        url=j.get("apply_url") or j.get("url") or "", posted_at=parse_posted_at(j.get("date") or j.get("epoch")),
        source="remoteok", description=short_desc(j.get("description") or ""))

def conv_remotive(j, source, hint=""):
    loc, title, tags = j.get("candidate_required_location") or "", j.get("title") or "", j.get("tags") or []
    c,st,ci=parse_location(loc)
    return record(id_=f"remotive:{j.get('id')}", title=title, company=j.get("company_name") or "",
        country=c,state=st,city=ci, remote=looks_remote([loc,title,tags],source),
        url=j.get("url") or "", posted_at=parse_posted_at(j.get("publication_date")),
        source="remotive", description=short_desc(j.get("description") or ""))

def conv_jobicy(j, source, hint=""):
    loc, title = j.get("jobGeo") or "", j.get("jobTitle") or ""
    c,st,ci=parse_location(loc)
    return record(id_=f"jobicy:{j.get('id')}", title=title, company=j.get("companyName") or "",
        country=c,state=st,city=ci, remote=looks_remote([loc,title,j.get("jobType")],source),
        url=j.get("url") or "", posted_at=parse_posted_at(j.get("pubDate")),
        source="jobicy", description=short_desc(j.get("jobExcerpt") or j.get("jobDescription") or ""))

def conv_arbeitnow(j, source, hint=""):
    if not truthy(j.get("remote")):
        return None
    loc, title, tags = j.get("location") or "", j.get("title") or "", j.get("tags") or []
    c,st,ci=parse_location(loc)
    if not c and loc:
        c,st,ci=parse_location(loc, "Germany")
        if not ci: ci=re.sub(r"\s+"," ",str(loc)).strip()
    return record(id_=f"arbeitnow:{j.get('slug') or j.get('url')}", title=title, company=j.get("company_name") or "",
        country=c,state=st,city=ci, remote=True,
        url=j.get("url") or "", posted_at=parse_posted_at(j.get("created_at")),
        source="arbeitnow", description=short_desc(j.get("description") or ""))

def conv_himalayas(j, source, hint=""):
    locs, title = j.get("locationRestrictions") or [], j.get("title") or ""
    c,st,ci=parse_location(locs)
    company=j.get("companyName") or ""
    if company.strip().lower() in {"name","company",""}:
        slug=j.get("companySlug") or ""
        company=slug.replace("-"," ").title() if slug else company
    url=j.get("applicationLink") or j.get("guid") or ""
    return record(id_=f"himalayas:{url or title}", title=title, company=company,
        country=c,state=st,city=ci, remote=looks_remote([locs,title],source),
        url=url, posted_at=parse_posted_at(j.get("pubDate")),
        source="himalayas", description=short_desc(j.get("excerpt") or j.get("description") or ""))

def conv_greenhouse(j, source, hint=""):
    loc=j.get("location"); loc_name=loc.get("name") if isinstance(loc,dict) else (str(loc) if loc else "")
    meta=[]
    for m in j.get("metadata") or []:
        if isinstance(m,dict) and m.get("name") in {"Job Posting Location","Location","Office Location","Location Type"}:
            val=m.get("value")
            if isinstance(val,list): meta.extend(str(x) for x in val)
            elif val: meta.append(str(val))
    offices=[]
    for o in j.get("offices") or []:
        if isinstance(o,dict):
            offices.append(o.get("name") or "")
            loc2=o.get("location")
            if isinstance(loc2,dict): offices.append(loc2.get("name") or "")
            elif loc2: offices.append(str(loc2))
    title=j.get("title") or ""
    c,st,ci=parse_location(meta, offices, loc_name)
    company=j.get("company_name") or company_from_url(j.get("absolute_url") or "", hint) or hint
    url=j.get("absolute_url") or ""
    if company.lower()=="remotecom": company="Remote"
    if company: company=company.replace("-"," ").title() if company==hint else company
    return record(id_=f"greenhouse:{slug_company(company) or slug_company(hint) or 'unknown'}:{j.get('id')}",
        title=title, company=company, country=c,state=st,city=ci,
        remote=looks_remote([loc_name,meta,offices,title],source),
        url=url, posted_at=parse_posted_at(j.get("first_published") or j.get("updated_at")),
        source="greenhouse", description=short_desc(j.get("content") or title))

def conv_lever(j, source, hint=""):
    cats=j.get("categories") or {}
    loc=cats.get("location") if isinstance(cats,dict) else ""
    all_locs=cats.get("allLocations") if isinstance(cats,dict) else []
    iso=j.get("country") or ""
    title=j.get("text") or j.get("title") or ""
    wtype=j.get("workplaceType") or ""
    remote=looks_remote([loc,all_locs,title,wtype],source, explicit=(wtype.lower() in {"remote","hybrid"} if isinstance(wtype,str) else None))
    c,st,ci=parse_location(loc, all_locs, ISO.get(str(iso).lower(), iso))
    url=j.get("hostedUrl") or j.get("applyUrl") or ""
    company=company_from_url(url, hint) or hint
    if company: company=company.replace("-"," ").title()
    return record(id_=f"lever:{slug_company(company) or 'unknown'}:{j.get('id')}", title=title, company=company,
        country=c,state=st,city=ci, remote=remote, url=url, posted_at=parse_posted_at(j.get("createdAt")),
        source="lever", description=short_desc(j.get("descriptionPlain") or j.get("description") or ""))

def conv_themuse(j, source, hint=""):
    loc_names=[]
    for loc in j.get("locations") or []:
        loc_names.append(loc.get("name") if isinstance(loc,dict) else str(loc))
    title=j.get("name") or ""
    refs=j.get("refs") or {}
    url=refs.get("landing_page") or refs.get("external_link") or "" if isinstance(refs,dict) else ""
    comp=j.get("company")
    company=comp.get("name") if isinstance(comp,dict) else ""
    c,st,ci=parse_location(loc_names)
    return record(id_=f"themuse:{j.get('id')}", title=title, company=company, country=c,state=st,city=ci,
        remote=looks_remote([loc_names,title,j.get("tags")],source), url=url,
        posted_at=parse_posted_at(j.get("publication_date")), source="themuse",
        description=short_desc(j.get("contents") or ""))

def conv_jobdata(j, source, hint=""):
    countries=j.get("countries") or []; cities=j.get("cities") or []; states=j.get("states") or []
    cname=countries[0].get("name") if countries and isinstance(countries[0],dict) else ""
    city_name=state_name=""
    if cities and isinstance(cities[0],dict):
        city_name=cities[0].get("name") or cities[0].get("asciiname") or ""
        st=cities[0].get("state")
        if isinstance(st,dict): state_name=st.get("name") or st.get("code") or ""
    if states and isinstance(states[0],dict) and not state_name:
        state_name=states[0].get("name") or states[0].get("code") or ""
    loc, title = j.get("location") or "", j.get("title") or ""
    c,st,ci=parse_location(cname, city_name, state_name, loc)
    comp=j.get("company")
    company=comp.get("name") if isinstance(comp,dict) else (comp if isinstance(comp,str) else "")
    return record(id_=f"jobdata:{j.get('id')}", title=title, company=company, country=c, state=st or state_name,
        city=ci or city_name, remote=looks_remote([loc,title,cname],source, explicit=j.get("has_remote")),
        url=j.get("application_url") or "", posted_at=parse_posted_at(j.get("published")),
        source="jobdata", description=short_desc(j.get("description") or ""))

def conv_workingnomads(j, source, hint=""):
    loc, title, tags = j.get("location") or "", j.get("title") or "", j.get("tags") or ""
    c,st,ci=parse_location(loc)
    return record(id_=f"workingnomads:{j.get('url') or title}", title=title, company=j.get("company_name") or "",
        country=c,state=st,city=ci, remote=looks_remote([loc,title,tags],source),
        url=j.get("url") or "", posted_at=parse_posted_at(j.get("pub_date")),
        source="workingnomads", description=short_desc(j.get("description") or ""))

def conv_ashby(j, source, hint=""):
    loc=j.get("location") or j.get("locationName") or ""
    if isinstance(loc,dict): loc=loc.get("name") or loc.get("locationName") or ""
    addr=j.get("address") or {}
    pa=addr.get("postalAddress") if isinstance(addr,dict) else None
    secs=[]
    for s in j.get("secondaryLocations") or []:
        if isinstance(s,dict):
            secs.append(s.get("location") or "")
            a=s.get("address") or {}
            if isinstance(a,dict) and a.get("postalAddress"):
                secs.append(a["postalAddress"])
    title=j.get("title") or j.get("jobTitle") or ""
    c,st,ci=parse_location(loc, pa, secs)
    url=j.get("jobUrl") or j.get("applyUrl") or j.get("url") or ""
    company=j.get("companyName") or j.get("company") or hint
    if isinstance(company,dict): company=company.get("name") or hint
    if company==hint and hint: company=hint.replace("-"," ").title()
    wtype=j.get("workplaceType") or ""
    remote=looks_remote([loc,title,wtype],source, explicit=j.get("isRemote") or (str(wtype).lower() in {"remote","hybrid"}))
    return record(id_=f"ashby:{j.get('id') or j.get('jobPostingId') or url}", title=title, company=str(company or ""),
        country=c,state=st,city=ci, remote=remote,
        url=url, posted_at=parse_posted_at(j.get("publishedAt") or j.get("publishedDate") or j.get("createdAt")),
        source="ashby", description=short_desc(j.get("descriptionPlain") or j.get("descriptionHtml") or j.get("description") or ""))

def conv_remotejobsorg(j, source, hint=""):
    loc=j.get("location") or ""
    title=j.get("title") or ""
    c,st,ci=parse_location(loc)
    comp=j.get("company")
    company=comp.get("name") if isinstance(comp,dict) else (comp or "")
    url=j.get("url") or j.get("apply_url") or ""
    return record(id_=f"remotejobsorg:{j.get('id') or url}", title=title, company=company,
        country=c,state=st,city=ci, remote=True, url=url,
        posted_at=parse_posted_at(j.get("posted_at")), source="remotejobsorg",
        description=short_desc(j.get("description") or ""))

def conv_rfj(j, source, hint=""):
    locs=j.get("locations") or []
    title=j.get("title") or ""
    c,st,ci=parse_location(locs)
    url=j.get("url") or ""
    return record(id_=f"remotefirstjobs:{j.get('id') or url}", title=title, company=j.get("company_name") or "",
        country=c,state=st,city=ci, remote=True, url=url,
        posted_at=parse_posted_at(j.get("published_at")), source="remotefirstjobs",
        description=short_desc(j.get("description") or ""))

def conv_workable(j, source, hint=""):
    loc=j.get("location") or {}
    loc_parts=[]
    if isinstance(loc, dict):
        loc_parts=[loc.get("city"), loc.get("region"), loc.get("country")]
        tele=loc.get("telecommuting")
    else:
        loc_parts=[loc]; tele=None
    title=j.get("title") or ""
    c,st,ci=parse_location(*loc_parts)
    url=j.get("url") or j.get("application_url") or j.get("shortlink") or ""
    company=j.get("department") or hint
    if isinstance(j.get("company"), dict): company=j["company"].get("name") or company
    remote=looks_remote(loc_parts+[title],source, explicit=tele)
    return record(id_=f"workable:{j.get('shortcode') or j.get('id') or url}", title=title,
        company=str(company or hint or "").replace("-"," ").title(),
        country=c,state=st,city=ci, remote=remote, url=url,
        posted_at=parse_posted_at(j.get("created_at") or j.get("published_on")),
        source="workable", description=short_desc(j.get("description") or ""))

def conv_mcf(j, source, hint=""):
    title=j.get("title") or j.get("jobTitle") or (j.get("metadata") or {}).get("jobTitle") or ""
    if isinstance(j.get("jobDetails"), dict):
        jd=j["jobDetails"]
        title=title or jd.get("title") or ""
    loc=j.get("location") or j.get("jobLocation") or ""
    if isinstance(j.get("metadata"), dict) and not loc:
        loc=j["metadata"].get("jobLocation") or j["metadata"].get("location") or ""
    addrs=j.get("address") or j.get("addresses") or []
    c,st,ci=parse_location(loc, addrs, j.get("ssocCode"), j.get("country"))
    url=j.get("metadata",{}).get("jobDetailUrl") if isinstance(j.get("metadata"),dict) else ""
    url=url or j.get("url") or j.get("jobUrl") or j.get("jobDetailUrl") or ""
    if not url and j.get("uuid"):
        url=f"https://www.mycareersfuture.gov.sg/job/{j.get('uuid')}"
    company=""
    adv=j.get("advertiser") or j.get("company") or {}
    if isinstance(adv, dict): company=adv.get("name") or adv.get("companyName") or ""
    elif isinstance(adv, str): company=adv
    posted=j.get("postedDate") or j.get("posted_at") or j.get("metadata",{}).get("postedDate") if isinstance(j.get("metadata"),dict) else j.get("postedDate")
    remote=looks_remote([loc,title,j.get("jobType")],source, explicit=j.get("isRemote"))
    return record(id_=f"mcf:{j.get('uuid') or j.get('id') or url}", title=title, company=company,
        country=c or "Singapore", state=st or "Singapore", city=ci,
        remote=remote, url=url, posted_at=parse_posted_at(posted),
        source="mcf", description=short_desc(j.get("description") or j.get("jobDescription") or ""))

def conv_generic(j, source, hint=""):
    title=j.get("title") or j.get("name") or j.get("position") or j.get("jobTitle") or ""
    url=j.get("url") or j.get("apply_url") or j.get("application_url") or j.get("absolute_url") or j.get("hostedUrl") or j.get("jobUrl") or ""
    company=j.get("company_name") or j.get("companyName") or ""
    if isinstance(j.get("company"), dict): company=company or j["company"].get("name") or ""
    elif isinstance(j.get("company"), str): company=company or j["company"]
    loc=j.get("location") or j.get("locations") or j.get("jobGeo") or ""
    c,st,ci=parse_location(loc)
    posted=j.get("posted_at") or j.get("publication_date") or j.get("published") or j.get("pubDate") or j.get("created_at") or j.get("publishedAt")
    remote=looks_remote([loc,title], source, explicit=j.get("remote") or j.get("isRemote") or j.get("has_remote"))
    return record(id_=f"{source}:{j.get('id') or url or title}", title=title, company=company,
        country=c,state=st,city=ci, remote=remote, url=url, posted_at=parse_posted_at(posted),
        source=source, description=short_desc(j.get("description") or j.get("excerpt") or j.get("contents") or ""))

CONVERTERS = {
    "remoteok":conv_remoteok,"remotive":conv_remotive,"jobicy":conv_jobicy,"arbeitnow":conv_arbeitnow,
    "himalayas":conv_himalayas,"greenhouse":conv_greenhouse,"lever":conv_lever,"themuse":conv_themuse,
    "jobdata":conv_jobdata,"workingnomads":conv_workingnomads,"ashby":conv_ashby,
    "remotejobsorg":conv_remotejobsorg,"remotefirstjobs":conv_rfj,"workable":conv_workable,"mcf":conv_mcf,
}

def rss_tag(block, name):
    m=re.search(rf"<{name}(?:\s[^>]*)?>(.*?)</{name}>", block, flags=re.S|re.I)
    if not m: return ""
    val=re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S)
    return html.unescape(val).strip()

def parse_rss_items(text):
    items=[]
    for m in re.finditer(r"<item>(.*?)</item>", text, flags=re.S|re.I):
        b=m.group(1)
        items.append({"title":rss_tag(b,"title"),"link":rss_tag(b,"link") or rss_tag(b,"guid"),
            "pubDate":rss_tag(b,"pubDate"),"description":rss_tag(b,"description"),
            "region":rss_tag(b,"region"),"country":rss_tag(b,"country"),"state":rss_tag(b,"state")})
    return items

def conv_wwr(it):
    raw=it.get("title") or ""
    company, title = ("", raw)
    if ":" in raw:
        company, title = raw.split(":",1); company, title = company.strip(), title.strip()
    loc_parts=[it.get("country") or "", it.get("state") or "", it.get("region") or ""]
    desc=it.get("description") or ""
    hq=re.search(r"Headquarters:</strong>\s*([^<]+)", desc, re.I)
    if hq: loc_parts.append(hq.group(1))
    c,st,ci=parse_location(*loc_parts)
    url=it.get("link") or ""
    return record(id_=f"weworkremotely:{url or raw}", title=title or raw, company=company,
        country=c,state=st,city=ci, remote=True, url=url, posted_at=parse_posted_at(it.get("pubDate")),
        source="weworkremotely", description=short_desc(desc))

def coerce_existing(row):
    if not isinstance(row, dict): return None
    url=normalize_url(row.get("url")); title=strip_html(row.get("title") or "")
    if not url or not title: return None
    source=str(row.get("source") or "").strip() or "unknown"
    country=row.get("country") or ""
    if country not in TARGET_SET: country=""
    remote=bool(row.get("remote"))
    if source=="arbeitnow" and not remote: return None
    if not remote and country not in TARGET_SET: return None
    posted=row.get("posted_at")
    if posted=="": posted=None
    elif posted is not None: posted=parse_posted_at(posted) or (str(posted) if str(posted) else None)
    city=str(row.get("city") or "")
    state=fill_state(country, str(row.get("state") or ""), city)
    return {"id":str(row.get("id") or f"{source}:{url}"),"title":title,"company":strip_html(row.get("company") or ""),
        "country":country,"state":state,"city":city,
        "remote":remote,"url":url,"posted_at":posted,"source":source,
        "description":short_desc(row.get("description") or "") if row.get("description") else ""}

def richness(row):
    return (1 if row.get("country") else 0, 1 if row.get("city") else 0, 1 if row.get("state") else 0,
            len(row.get("description") or ""), 1 if row.get("posted_at") else 0, 1 if row.get("company") else 0)

def merge_rows(rows):
    by={}
    for r in rows:
        if not r: continue
        prev=by.get(r["url"])
        if prev is None or richness(r)>richness(prev): by[r["url"]]=r
    return list(by.values())

def atomic_write_lines(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line if line.endswith("\n") else line+"\n")
    tmp.replace(path)

def write_jsonl(path, rows):
    lines=[json.dumps({k: (bool(r.get("remote")) if k=="remote" else ("" if r.get(k) is None and k=="posted_at" else r.get(k))) for k in KEYS}, ensure_ascii=False, separators=(",",":")) for r in rows]
    atomic_write_lines(path, lines)

def file_hint(name):
    stem=Path(name).stem
    for pref in ("gh_","lever_","ashby_","greenhouse_","workable_","mcf_"):
        if stem.startswith(pref): return stem[len(pref):]
    return ""

def process_raw(path):
    name=path.name
    if name in SKIP_EXACT: return [], "internal/log file"
    if name.startswith("_"): return [], "underscore sidecar (not a job dump)"
    if name.endswith(SKIP_SUFF): return [], f"skipped suffix {path.suffix}"
    src_guess=source_from_name(name); hint=file_hint(name)
    if name.endswith((".rss",".xml")) or (src_guess=="weworkremotely" and path.suffix in {".rss",".xml",""}):
        try: text=path.read_text(encoding="utf-8", errors="replace")
        except OSError as e: return [], f"read error: {e}"
        if "<item" not in text.lower(): return [], "xml/rss without <item> entries"
        items=parse_rss_items(text)
        if not items: return [], "rss parsed 0 items"
        return [r for r in (conv_wwr(it) for it in items) if r], None
    data, err = load_json_file(path)
    if err and not isinstance(data,(dict,list)):
        if isinstance(data,str) and "<item" in data.lower():
            return [r for r in (conv_wwr(it) for it in parse_rss_items(data)) if r], None
        return [], err
    if err: return [], err
    jobs=extract_jobs(data)
    if not jobs: return [], "no job list found"
    schema=None
    for j in jobs:
        schema=detect_schema(j)
        if schema: break
    schema=schema or src_guess
    if not schema: return [], f"unrecognized job schema keys={list(jobs[0].keys())[:12]}"
    conv=CONVERTERS.get(schema) or conv_generic
    rows=[]
    for j in jobs:
        try: rec=conv(j, schema, hint)
        except Exception: rec=None
        if rec: rows.append(rec)
    return rows, None

def load_existing_jsonl(path):
    out=[]
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            try: row=json.loads(line)
            except json.JSONDecodeError: continue
            c=coerce_existing(row)
            if c: out.append(c)
    except OSError:
        return out
    return out

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(path.name+".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    tmp.replace(path)

def country_counts(jobs):
    raw=Counter(j["country"] for j in jobs)
    out={}
    for name in TARGET:
        if name in raw: out[name]=raw[name]
    extras=sorted(k for k in raw if k not in TARGET and k!="")
    for name in extras: out[name]=raw[name]
    if "" in raw: out[""]=raw[""]
    return out

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    parsed={}
    n_ok=n_skip=n_raw=0
    files=sorted(p for p in RAW.iterdir() if p.is_file()) if RAW.exists() else []
    for path in files:
        rows, reason = process_raw(path)
        if reason and not rows:
            n_skip += 1
            continue
        if not rows:
            n_skip += 1
            continue
        src=rows[0]["source"]
        parsed.setdefault(src, []).extend(rows)
        n_ok += 1
        n_raw += len(rows)
    print(f"RAW files ok={n_ok} skip={n_skip} rows={n_raw}")

    # Merge existing per-source jsonl (fill gaps; Arbeitnow on-site dropped in coerce)
    if OUT.exists():
        for p in sorted(OUT.iterdir()):
            if p.suffix==".jsonl" and p.name not in {"all.jsonl"}:
                prev=load_existing_jsonl(p)
                if prev:
                    src=prev[0]["source"]
                    parsed.setdefault(src, []).extend(prev)
                    print(f"MERGE existing {p.name}: {len(prev)}")

    all_rows=[]
    per={}
    for src, rows in parsed.items():
        merged=merge_rows(rows)
        merged.sort(key=lambda r: (r.get("posted_at") or "", r.get("id") or ""))
        per[src]=merged
        all_rows.extend(merged)
        write_jsonl(OUT/f"{src}.jsonl", merged)
        print(f"WRITE {src}.jsonl ({len(merged)})")

    unique=merge_rows(all_rows)
    unique.sort(key=lambda r: (r.get("source") or "", r.get("posted_at") or "", r.get("id") or ""))
    write_jsonl(OUT/"all.jsonl", unique)
    write_jsonl(COMBINED, unique)

    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    by_s=dict(sorted(Counter(r["source"] for r in unique).items()))
    by_c=country_counts(unique)
    rem=sum(1 for r in unique if r["remote"])
    summary={
        "total": len(unique),
        "by_source": by_s,
        "by_country": by_c,
        "by_remote": {"remote": rem, "onsite": len(unique)-rem},
        "updated_at": now,
    }
    write_json(SUMMARY, summary)
    write_json(OUT/"stats.json", summary)
    print("\n==== SUMMARY ====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0

if __name__=="__main__":
    sys.exit(main())

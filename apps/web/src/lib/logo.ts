/** Resolve a company logo domain from an employer apply URL. Never use ATS vendor hosts as the mark. */

const ATS_VENDORS = [
  "greenhouse.io",
  "lever.co",
  "ashbyhq.com",
  "myworkdayjobs.com",
  "smartrecruiters.com",
  "icims.com",
] as const;

/** Never use a job-board host as the company mark. */
const AGGREGATOR_HOSTS = [
  "himalayas.app",
  "himalayas.com",
  "remoteok.com",
  "remoteok.io",
  "remotive.com",
  "remotive.io",
  "weworkremotely.com",
  "jobicy.com",
  "workingnomads.com",
  "workingnomads.co",
  "arbeitnow.com",
  "themuse.com",
  "europa.eu",
  "jobsyn.org",
  "linkedin.com",
  "indeed.com",
  "naukri.com",
  "instahyre.com",
  "internshala.com",
  "wellfound.com",
  "angel.co",
  "glassdoor.com",
  "ziprecruiter.com",
  "simplyhired.com",
  "dice.com",
  "monster.com",
  "careerbuilder.com",
] as const;

/** ATS board slugs (and company-name keys) that are not `{slug}.com`. */
const KNOWN_DOMAINS: Record<string, string> = {
  stripe: "stripe.com",
  openai: "openai.com",
  airbnb: "airbnb.com",
  nvidia: "nvidia.com",
  databricks: "databricks.com",
  mongodb: "mongodb.com",
  mongodbinc: "mongodb.com",
  elastic: "elastic.co",
  elasticco: "elastic.co",
  gomotive: "motive.com",
  motive: "motive.com",
  photoroom: "photoroom.com",
  coinbase: "coinbase.com",
  dropbox: "dropbox.com",
  instacart: "instacart.com",
  fivetran: "fivetran.com",
  apple: "apple.com",
  google: "google.com",
  meta: "meta.com",
  amazon: "amazon.com",
  microsoft: "microsoft.com",
  netflix: "netflix.com",
  uber: "uber.com",
  shopify: "shopify.com",
  snowflake: "snowflake.com",
  cloudflare: "cloudflare.com",
  notion: "notion.so",
  figma: "figma.com",
  slack: "slack.com",
  zoom: "zoom.us",
  salesforce: "salesforce.com",
  adobe: "adobe.com",
  tesla: "tesla.com",
  spacex: "spacex.com",
  bjak: "bjak.com",
  bjakcareer: "bjak.com",
  npr: "npr.org",
  nationalpublicradioinc: "npr.org",
  intercom: "intercom.com",
  adyen: "adyen.com",
  affirm: "affirm.com",
  algolia: "algolia.com",
  amplitude: "amplitude.com",
  anaplan: "anaplan.com",
  anduril: "anduril.com",
  andurilindustries: "anduril.com",
  benchling: "benchling.com",
  backblaze: "backblaze.com",
  tenable: "tenable.com",
  tenableinc: "tenable.com",
  dnb: "dnb.com",
  dunbradstreet: "dnb.com",
  wmg: "wmg.com",
  warnermusic: "wmg.com",
  alarmcom: "alarm.com",
  ezcater: "ezcater.com",
  ezcaterinc: "ezcater.com",
  bt: "bt.com",
  btgroup: "bt.com",
  lpcorp: "lpcorp.com",
};

const COMPOUND_TLDS = new Set([
  "co.uk",
  "org.uk",
  "ac.uk",
  "gov.uk",
  "com.au",
  "net.au",
  "org.au",
  "co.in",
  "com.br",
  "co.nz",
  "co.jp",
  "com.sg",
  "co.za",
  "com.mx",
  "co.kr",
  "com.hk",
  "co.id",
]);

function normKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function hostOf(url: string): string {
  return url.toLowerCase().replace(/^\.+/, "");
}

export function isAtsVendorHost(host: string): boolean {
  const h = hostOf(host);
  return ATS_VENDORS.some((v) => h === v || h.endsWith(`.${v}`));
}

export function isAggregatorHost(host: string): boolean {
  const h = hostOf(host);
  return AGGREGATOR_HOSTS.some((v) => h === v || h.endsWith(`.${v}`) || h.includes(v));
}

function isBlockedLogoHost(host: string): boolean {
  return isAtsVendorHost(host) || isAggregatorHost(host);
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    value,
  );
}

function firstPathSegment(pathname: string): string {
  return pathname.split("/").filter(Boolean)[0] ?? "";
}

function knownDomain(token: string): string | undefined {
  const raw = token.toLowerCase().replace(/_/g, "-");
  return KNOWN_DOMAINS[normKey(raw)] ?? KNOWN_DOMAINS[raw];
}

function slugToDomain(slug: string): string | null {
  const trimmed = slug.trim();
  if (!trimmed || isUuid(trimmed)) return null;
  const mapped = knownDomain(trimmed);
  if (mapped) return mapped;
  const lower = trimmed.toLowerCase().replace(/_/g, "-");
  if (lower.includes(".")) {
    return isBlockedLogoHost(lower) ? null : lower;
  }
  return `${lower}.com`;
}

function atsCompanySlug(host: string, pathname: string): string | null {
  const h = hostOf(host);

  if (
    h === "greenhouse.io" ||
    h.endsWith(".greenhouse.io") ||
    h === "lever.co" ||
    h.endsWith(".lever.co") ||
    h === "ashbyhq.com" ||
    h.endsWith(".ashbyhq.com")
  ) {
    const slug = firstPathSegment(pathname);
    return slug && !isUuid(slug) ? slug : null;
  }

  if (h.endsWith("myworkdayjobs.com")) {
    const labels = h.split(".");
    const left = labels.slice(0, -2);
    const tenant = left.find((label) => !/^wd\d+$/i.test(label) && label !== "www");
    return tenant ?? null;
  }

  if (h.endsWith("smartrecruiters.com")) {
    const parts = pathname.split("/").filter(Boolean);
    const idx = parts.findIndex((p) => p.toLowerCase() === "companies");
    if (idx >= 0 && parts[idx + 1] && !isUuid(parts[idx + 1])) return parts[idx + 1];
    const slug = parts[0];
    if (slug && slug.toLowerCase() !== "v1" && !isUuid(slug)) return slug;
    return null;
  }

  if (h.endsWith("icims.com")) {
    const sub = h.split(".")[0] ?? "";
    if (!sub || sub === "www" || sub === "careers") return null;
    return sub.replace(/^careers-/, "");
  }

  return null;
}

export function registrableDomain(host: string): string {
  const h = hostOf(host).replace(/^www\./, "");
  const parts = h.split(".").filter(Boolean);
  if (parts.length <= 2) return h;
  const last2 = parts.slice(-2).join(".");
  if (COMPOUND_TLDS.has(last2)) return parts.slice(-3).join(".");
  return last2;
}

function domainFromCompany(company?: string): string | null {
  if (!company) return null;
  const exact = knownDomain(company);
  if (exact) return exact;
  const first = company.split(/\s+/).filter(Boolean)[0];
  return first ? (knownDomain(first) ?? null) : null;
}

/** Company website domain for a favicon, or null when we should show initials. */
export function logoDomain(url: string, company?: string): string | null {
  if (url) {
    try {
      const parsed = new URL(url);
      const host = parsed.hostname.toLowerCase();
      const slug = atsCompanySlug(host, parsed.pathname);
      if (slug) {
        const domain = slugToDomain(slug);
        if (domain && !isBlockedLogoHost(domain)) return domain;
      }
      if (!isBlockedLogoHost(host)) {
        const reg = registrableDomain(host);
        if (reg && !isBlockedLogoHost(reg)) {
          return knownDomain(reg.split(".")[0] ?? "") ?? reg;
        }
      }
    } catch {
      /* fall through to company name */
    }
  }
  return domainFromCompany(company);
}

export function logoUrl(domain: string): string {
  return `https://icons.duckduckgo.com/ip3/${encodeURIComponent(domain)}.ico`;
}

export function fallbackLogoUrl(domain: string): string {
  return `https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://${encodeURIComponent(domain)}&size=128`;
}

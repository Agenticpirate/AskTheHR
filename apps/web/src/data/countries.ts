export const COUNTRIES = [
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
] as const;

export type Country = (typeof COUNTRIES)[number];

export const COUNTRY_META: Record<
  Country,
  { flag: string; blurb: string; slug: string }
> = {
  USA: {
    flag: "🇺🇸",
    slug: "usa",
    blurb: "The deepest remote market. Tech, ops, and product roles across every timezone.",
  },
  India: {
    flag: "🇮🇳",
    slug: "india",
    blurb: "Engineering and IT-services volume, plus a growing fully-remote layer.",
  },
  Canada: {
    flag: "🇨🇦",
    slug: "canada",
    blurb: "US-adjacent remote culture with strong hubs in Toronto, Vancouver, and Montreal.",
  },
  UK: {
    flag: "🇬🇧",
    slug: "uk",
    blurb: "London plus a real remote-UK bucket. Product, finance, and design stay busy.",
  },
  Australia: {
    flag: "🇦🇺",
    slug: "australia",
    blurb: "Sydney and Melbourne lead. Fully-remote is thinner — still worth a weekly pass.",
  },
  Germany: {
    flag: "🇩🇪",
    slug: "germany",
    blurb: "Office-leaning, but Berlin and Munich still post hybrid and remote-in-country roles.",
  },
  Netherlands: {
    flag: "🇳🇱",
    slug: "netherlands",
    blurb: "One of Europe's more remote-friendly markets. Amsterdam is the default hub.",
  },
  Ireland: {
    flag: "🇮🇪",
    slug: "ireland",
    blurb: "Dublin multinationals and a useful Remote-Ireland layer for the rest of the island.",
  },
  Singapore: {
    flag: "🇸🇬",
    slug: "singapore",
    blurb: "A city-state market. On-site is easy; remote roles are fewer and more senior.",
  },
  France: {
    flag: "🇫🇷",
    slug: "france",
    blurb: "Paris-heavy, hybrid-common. Remote-France exists — it just is not the default.",
  },
};

export function countryFromSlug(slug: string): Country | undefined {
  const lower = slug.toLowerCase();
  return COUNTRIES.find((c) => COUNTRY_META[c].slug === lower);
}

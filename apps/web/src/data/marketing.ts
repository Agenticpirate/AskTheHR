export const SITE_URL = "https://askthehr.com";
export const SITE_NAME = "AskTheHR";
export const SUPPORT_EMAIL = "support@0pening.com";

export const SITE_TITLE =
  "AskTheHR — Cadence. The job search fails on discipline, not information.";

export const SITE_DESCRIPTION =
  "AskTheHR builds Cadence, paid accountability for the job search. 0penings is the free employer-direct job board inside Cadence. Worldwide from $4.99/month. India from ₹199/month.";

export type Region = "world" | "in";

export type PlanId = "monthly" | "yearly" | "lifetime";

export type PlanPrice = {
  id: PlanId;
  name: string;
  cadence: string;
  featured?: boolean;
  badge?: string;
  world: { amount: string; period: string; note: string };
  in: { amount: string; period: string; note: string };
};

export const PLANS: PlanPrice[] = [
  {
    id: "monthly",
    name: "Monthly",
    cadence: "Billed every month",
    world: { amount: "$4.99", period: "/ month", note: "Cancel when the search ends." },
    in: { amount: "₹199", period: "/ month", note: "Cancel when the search ends." },
  },
  {
    id: "yearly",
    name: "Yearly",
    cadence: "Billed once a year",
    featured: true,
    badge: "Most used",
    world: { amount: "$39.99", period: "/ year", note: "One charge. Twelve months of Cadence." },
    in: { amount: "₹1,499", period: "/ year", note: "One charge. Twelve months of Cadence." },
  },
  {
    id: "lifetime",
    name: "Lifetime",
    cadence: "Pay once",
    world: { amount: "$99", period: " once", note: "Cadence on this product, no renewals." },
    in: { amount: "₹3,999", period: " once", note: "Cadence on this product, no renewals." },
  },
];

export type FaqItem = {
  id: string;
  question: string;
  answer: string;
};

export const FAQS: FaqItem[] = [
  {
    id: "what-is-cadence",
    question: "What is Cadence?",
    answer:
      "Cadence is AskTheHR’s paid accountability product. You pick Fresh or Experienced, run daily rings for time, tailored applications, skills, and outreach, then hit a weekly number. Make the week and it counts. Miss it and the streak resets. The loop lives on this device until auth ships.",
  },
  {
    id: "what-is-0penings",
    question: "What is 0penings?",
    answer:
      "0penings (digit zero) is the free employer-direct job board inside Cadence. It is a discovery slice across ten countries. Apply opens the employer career site or ATS. AskTheHR does not take the application.",
  },
  {
    id: "is-it-a-job-board",
    question: "Is AskTheHR a job board?",
    answer:
      "AskTheHR is the company. Cadence is paid accountability. 0penings is a free board for finding roles — not a marketplace, not an aggregator that collects applications, and not an ATS. If you need a feed of other people’s jobs with a form in the middle, this is not that.",
  },
  {
    id: "pricing",
    question: "How much does Cadence cost?",
    answer:
      "Worldwide: $4.99 per month, $39.99 per year, or $99 lifetime. India: ₹199 per month, ₹1,499 per year, or ₹3,999 lifetime. Yearly is marked Most used because it is the plan we expect people to pick for a real search. 0penings stays free.",
  },
  {
    id: "account",
    question: "Do I need an account?",
    answer:
      "No account is required to start. Your track, target, application log, and optional 0pening name live in this browser. Clearing site data clears them. A public streak on the board is opt-in.",
  },
  {
    id: "apply",
    question: "Where do applications go?",
    answer:
      "To the employer. 0penings links to the company career page or applicant tracking system. We do not route you through third-party job boards, and we do not submit on your behalf.",
  },
  {
    id: "miss-a-week",
    question: "What happens if I miss a week?",
    answer:
      "The weekly streak resets. That is the product. Cadence is not a motivational quote. Hit the number and the week counts. Miss it and you start the streak again. Daily check-in and the application log stay so the week stays honest.",
  },
];

export const HOW_STEPS = [
  {
    n: "01",
    title: "Pick a track",
    body: "Fresh or Experienced. Daily minutes, tailored apps, skills, and outreach stay executable. Vague weekly targets fail.",
  },
  {
    n: "02",
    title: "Run the rings",
    body: "Check in. Log time, applications, skill work, and outreach. The day has a number. Cadence keeps it visible.",
  },
  {
    n: "03",
    title: "Apply on the employer site",
    body: "0penings is discovery. Open the role, apply where the company hires, then log it so the week stays honest.",
  },
  {
    n: "04",
    title: "Hit the week",
    body: "Make the weekly number and the week counts. Miss it and the streak resets. Reminders stay on the device; WhatsApp is paid.",
  },
] as const;

export const BENTO = [
  {
    id: "cadence",
    kicker: "Cadence",
    title: "Paid accountability",
    body: "Daily check-in, weekly target, streak, XP, and badges. The week is binary.",
    span: "md:col-span-3",
  },
  {
    id: "rings",
    kicker: "Daily rings",
    title: "Time, apps, skills, outreach",
    body: "Four rings. Fresh and Experienced ship with different daily numbers. You can change them later.",
    span: "md:col-span-3",
  },
  {
    id: "board",
    kicker: "0penings",
    title: "Employer-direct board",
    body: "Remote-first roles across ten countries. Apply leaves this site. No jobs.json on this page — open the board when you want the slice.",
    span: "md:col-span-4",
  },
  {
    id: "markets",
    kicker: "Markets",
    title: "Ten countries",
    body: "USA, India, Canada, UK, Australia, Germany, Netherlands, Ireland, Singapore, France.",
    span: "md:col-span-2",
  },
  {
    id: "reminders",
    kicker: "Reminders",
    title: "The day does not disappear",
    body: "Browser notifications are free. WhatsApp reminders are a paid Cadence plan. Messaging stops when the plan ends.",
    span: "md:col-span-3",
  },
  {
    id: "public",
    kicker: "Board",
    title: "Opt-in public streak",
    body: "Publish a nickname, track, and streak. Ranked by daily streak, then weekly streak, then XP. No accounts.",
    span: "md:col-span-3",
  },
] as const;

export function detectRegion(): Region {
  if (typeof window === "undefined") return "world";
  const params = new URLSearchParams(window.location.search);
  const forced = params.get("region");
  if (forced === "in") return "in";
  if (forced === "world") return "world";
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (tz === "Asia/Kolkata" || tz === "Asia/Calcutta") return "in";
  const lang = (navigator.language ?? "").toLowerCase();
  if (lang === "en-in" || lang.startsWith("hi") || lang.endsWith("-in")) return "in";
  return "world";
}

export function writeRegionParam(region: Region) {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (region === "in") url.searchParams.set("region", "in");
  else url.searchParams.delete("region");
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

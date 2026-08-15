import type { Plan, ReminderPrefs, WhatsAppPrefs } from "./tracker";

export const DEFAULT_REMINDER_TIME = "09:00";
export const DEFAULT_REMINDER_TZ = "Asia/Calcutta";

export function normalizeTime(value: string): string {
  const m = /^(\d{1,2}):(\d{2})/.exec(value.trim());
  if (!m) return DEFAULT_REMINDER_TIME;
  const h = Math.min(23, Math.max(0, Number(m[1])));
  const min = Math.min(59, Math.max(0, Number(m[2])));
  return `${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}`;
}

export function wallClock(
  now: Date,
  timeZone: string = DEFAULT_REMINDER_TZ,
): { hhmm: string; date: string } {
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const parts = Object.fromEntries(fmt.formatToParts(now).map((p) => [p.type, p.value]));
  return {
    hhmm: `${parts.hour}:${parts.minute}`,
    date: `${parts.year}-${parts.month}-${parts.day}`,
  };
}

export function shouldFireReminder(now: Date, reminder: ReminderPrefs): boolean {
  if (!reminder.enabled) return false;
  const { hhmm, date } = wallClock(now, reminder.timezone || DEFAULT_REMINDER_TZ);
  if (reminder.lastFired === date) return false;
  return hhmm >= normalizeTime(reminder.time || DEFAULT_REMINDER_TIME);
}

export function notifyBrowser(title: string, body: string): boolean {
  if (typeof Notification === "undefined") return false;
  if (Notification.permission !== "granted") return false;
  try {
    new Notification(title, { body, tag: "0pening-daily" });
    return true;
  } catch {
    return false;
  }
}

export type RemindResponse = {
  ok: boolean;
  reason?: string;
  queued?: boolean;
};

export async function requestWhatsAppRemind(input: {
  plan: Plan;
  whatsapp: WhatsAppPrefs;
}): Promise<RemindResponse> {
  try {
    const res = await fetch("/api/remind", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        plan: input.plan,
        whatsapp: input.whatsapp,
      }),
    });
    const data = (await res.json()) as RemindResponse;
    return data;
  } catch {
    return { ok: false, reason: "network" };
  }
}

export async function fireDailyReminder(input: {
  reminder: ReminderPrefs;
  plan: Plan;
  whatsapp: WhatsAppPrefs;
}): Promise<boolean> {
  notifyBrowser("0pening", "Time to check in. Stay in the hunt.");
  if (input.plan === "paid" && input.whatsapp.enabled) {
    await requestWhatsAppRemind({ plan: input.plan, whatsapp: input.whatsapp });
  }
  return true;
}

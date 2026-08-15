import { Lock } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { requestWhatsAppRemind } from "@/lib/reminders";
import { useTracker } from "@/lib/useTracker";

export function ReminderSettings() {
  const tracker = useTracker();
  const paid = tracker.plan === "paid";
  const [ping, setPing] = useState<string>("");
  const [perm, setPerm] = useState<string>(
    typeof Notification === "undefined" ? "unsupported" : Notification.permission,
  );

  const enableBrowser = async () => {
    if (typeof Notification === "undefined") {
      setPerm("unsupported");
      return;
    }
    const next = await Notification.requestPermission();
    setPerm(next);
    if (next === "granted") tracker.setReminder({ enabled: true });
  };

  const toggleBrowser = async () => {
    if (tracker.reminder.enabled) {
      tracker.setReminder({ enabled: false });
      return;
    }
    await enableBrowser();
  };

  const pingWhatsApp = async () => {
    const res = await requestWhatsAppRemind({
      plan: tracker.plan,
      whatsapp: tracker.whatsapp,
    });
    setPing(res.ok ? "Queued (official Cloud API stub)." : reasonCopy(res.reason));
  };

  return (
    <Card>
      <CardHeader>
        <div className="micro text-primary">Reminders</div>
        <CardTitle className="text-2xl tracking-tight">Stay on the clock.</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6">
        <div className="grid gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-medium">Browser reminder</div>
              <p className="mt-1 text-sm text-muted-foreground">
                Free. Fires once a day while this tab is open. Default 09:00 Asia/Calcutta.
              </p>
            </div>
            <Button
              type="button"
              variant={tracker.reminder.enabled ? "outline" : "default"}
              onClick={() => void toggleBrowser()}
            >
              {tracker.reminder.enabled ? "On" : "Enable"}
            </Button>
          </div>
          <label className="grid max-w-[220px] gap-1.5">
            <span className="micro">Daily time</span>
            <Input
              type="time"
              value={tracker.reminder.time}
              onChange={(e) => tracker.setReminder({ time: e.target.value })}
            />
          </label>
          <p className="text-xs text-muted-foreground">
            Timezone {tracker.reminder.timezone}.
            {perm === "denied"
              ? " Notifications are blocked in this browser."
              : perm === "unsupported"
                ? " This browser has no Notification API."
                : ""}{" "}
            After you close the tab, Web Push via Cloudflare is the free unlimited path — no Meta
            fees.
          </p>
        </div>

        <div className="h-px bg-border" />

        <label className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-medium">Paid plan</div>
            <p className="mt-1 text-sm text-muted-foreground">
              Local toggle until billing exists. WhatsApp turns off when this is off.
            </p>
          </div>
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={paid}
            onChange={(e) => tracker.setPlan(e.target.checked ? "paid" : "free")}
            aria-label="Paid plan"
          />
        </label>

        <div className={`grid gap-3 rounded-lg p-4 ring-1 ring-border ${paid ? "" : "opacity-70"}`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-medium">WhatsApp reminders</div>
              {!paid ? (
                <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Lock className="size-3.5" />
                  Paid plan — stops when the plan ends.
                </p>
              ) : (
                <p className="mt-1 text-sm text-muted-foreground">
                  Official Cloud API only. Template sends are billed by Meta. Turns off if you
                  cancel.
                </p>
              )}
            </div>
            <input
              type="checkbox"
              className="mt-1 size-4 accent-primary"
              checked={paid && tracker.whatsapp.enabled}
              disabled={!paid}
              onChange={(e) =>
                tracker.setWhatsApp({
                  enabled: e.target.checked,
                  optedIn: e.target.checked ? true : tracker.whatsapp.optedIn,
                })
              }
              aria-label="Enable WhatsApp reminders"
            />
          </div>
          <label className="grid max-w-xs gap-1.5">
            <span className="micro">Phone</span>
            <Input
              type="tel"
              inputMode="tel"
              placeholder="+91…"
              disabled={!paid}
              value={tracker.whatsapp.phone}
              onChange={(e) => tracker.setWhatsApp({ phone: e.target.value })}
            />
          </label>
          <p className="text-xs text-muted-foreground">
            Free users get browser reminders. WhatsApp is paid-only and turns off when the plan
            ends. There is no official free unlimited outbound blast.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="outline" size="sm" onClick={() => void pingWhatsApp()}>
              Ping Cloud API stub
            </Button>
            {ping ? <span className="text-xs text-muted-foreground">{ping}</span> : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function reasonCopy(reason?: string): string {
  if (reason === "paid_plan_required") return "Paid plan required.";
  if (reason === "whatsapp_disabled") return "WhatsApp is off.";
  if (reason === "whatsapp_not_configured") return "Cloud API not configured (501).";
  if (reason === "network") return "Could not reach /api/remind.";
  return reason || "Not sent.";
}

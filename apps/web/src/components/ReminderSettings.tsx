import { Lock } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
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
    <div className="rounded-lg bg-card ring-1 ring-border">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="min-w-0">
          <div className="micro text-primary">Reminders</div>
          <div className="mt-1 text-sm tracking-tight">Browser · free daily ping</div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {tracker.reminder.timezone}
            {perm === "denied"
              ? " · notifications blocked"
              : perm === "unsupported"
                ? " · no Notification API"
                : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="time"
            value={tracker.reminder.time}
            onChange={(e) => tracker.setReminder({ time: e.target.value })}
            className="h-8 w-[7.5rem]"
            aria-label="Daily reminder time"
          />
          <Button
            type="button"
            size="sm"
            variant={tracker.reminder.enabled ? "outline" : "default"}
            onClick={() => void toggleBrowser()}
          >
            {tracker.reminder.enabled ? "On" : "Enable"}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-2.5">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-3.5 accent-primary"
            checked={paid}
            onChange={(e) => tracker.setPlan(e.target.checked ? "paid" : "free")}
            aria-label="Paid plan"
          />
          Paid plan
        </label>
        <p className="text-xs text-muted-foreground">WhatsApp turns off when this is off.</p>
      </div>

      <div className={`border-t px-4 py-3 ${paid ? "" : "opacity-70"}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm font-medium">WhatsApp</div>
            {!paid ? (
              <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Lock className="size-3" />
                Paid-only · stops when the plan ends
              </p>
            ) : (
              <p className="mt-0.5 text-xs text-muted-foreground">
                Official Cloud API. Meta bills templates.
              </p>
            )}
          </div>
          <input
            type="checkbox"
            className="size-3.5 accent-primary"
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
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Input
            type="tel"
            inputMode="tel"
            placeholder="+91…"
            disabled={!paid}
            value={tracker.whatsapp.phone}
            onChange={(e) => tracker.setWhatsApp({ phone: e.target.value })}
            className="h-8 max-w-[12rem]"
            aria-label="WhatsApp phone"
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8"
            disabled={!paid}
            onClick={() => void pingWhatsApp()}
          >
            Ping stub
          </Button>
          {ping ? <span className="text-xs text-muted-foreground">{ping}</span> : null}
        </div>
      </div>
    </div>
  );
}

function reasonCopy(reason?: string): string {
  if (reason === "paid_plan_required") return "Paid plan required.";
  if (reason === "whatsapp_disabled") return "WhatsApp is off.";
  if (reason === "whatsapp_not_configured") return "Cloud API not configured (501).";
  if (reason === "network") return "Could not reach /api/remind.";
  return reason || "Not sent.";
}

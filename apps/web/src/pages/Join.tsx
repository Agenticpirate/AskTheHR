import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Orb } from "@/components/Orb";
import { PageEnter, Section } from "@/components/PageEnter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { checkUsername, claimUsernameRemote } from "@/lib/username-api";
import { isReservedUsername } from "@/data/reserved-usernames";
import { parseUsername, reasonMessage, type UsernameReason } from "@/lib/username";
import { useTracker } from "@/lib/useTracker";

type Status = "idle" | "checking" | UsernameReason;

export function Join() {
  const tracker = useTracker();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState(tracker.profile.email ?? "");
  const [status, setStatus] = useState<Status>("idle");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(Boolean(tracker.profile.username));

  useEffect(() => {
    const current = tracker.profile.username;
    if (!current) return;
    if (isReservedUsername(current)) {
      tracker.markUsernameReclaimed();
      setDone(false);
      return;
    }
    let live = true;
    void checkUsername(current).then((r) => {
      if (!live) return;
      if (r.reason === "reserved") {
        tracker.markUsernameReclaimed();
        setDone(false);
      }
    });
    return () => {
      live = false;
    };
  }, [tracker.profile.username]);

  useEffect(() => {
    const raw = username;
    if (!raw.trim()) {
      setStatus("idle");
      return;
    }
    const parsed = parseUsername(raw);
    if (!parsed) {
      setStatus("invalid");
      return;
    }
    if (isReservedUsername(parsed)) {
      setStatus("reserved");
      return;
    }
    setStatus("checking");
    const handle = window.setTimeout(() => {
      void checkUsername(parsed).then((r) => {
        setStatus(r.reason);
      });
    }, 280);
    return () => window.clearTimeout(handle);
  }, [username]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const parsed = parseUsername(username);
    if (!parsed || busy) return;
    setBusy(true);
    const remote = await claimUsernameRemote(parsed, displayName);
    if (!remote.ok) {
      setStatus(remote.reason ?? "invalid");
      setBusy(false);
      return;
    }
    tracker.claimUsername(parsed, { displayName, email });
    setDone(true);
    setBusy(false);
  };

  const reclaimed = Boolean(tracker.profile.usernameReclaimed) && !tracker.profile.username;
  const claimed = tracker.profile.username;
  const canSubmit = status === "ok" && !busy;

  if (done && claimed) {
    return (
      <PageEnter>
        <Section>
          <div className="micro text-primary">Yours</div>
          <h1 className="mt-3 text-5xl tracking-tight md:text-6xl">@{claimed}</h1>
          <p className="mt-4 max-w-lg text-base text-muted-foreground">
            That name is on this device. A username is a license, not property.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild>
              <Link to="/me">Open Me</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/terms">Terms</Link>
            </Button>
          </div>
        </Section>
      </PageEnter>
    );
  }

  return (
    <PageEnter>
      <Section>
        <div className="micro text-primary">Join</div>
        <h1 className="mt-3 text-5xl tracking-tight md:text-7xl">
          Claim your 0pening name.
        </h1>
        <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg">
          A short handle. Stored on this device for now. Brands and well-known
          names stay reserved.
        </p>
      </Section>

      {reclaimed ? (
        <Section delay={0.06} className="mt-8">
          <p className="max-w-xl text-sm text-muted-foreground">
            This name was released after a trademark request. Pick another.
          </p>
        </Section>
      ) : null}

      <Section delay={0.1} className="mt-10 max-w-xl">
        <form onSubmit={(e) => void onSubmit(e)} className="grid gap-8">
          <label className="grid gap-3">
            <span className="micro">Username</span>
            <div className="flex items-end gap-2 border-b border-border pb-2 focus-within:border-primary">
              <span className="pb-1 font-mono text-2xl text-muted-foreground md:text-3xl">@</span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value.toLowerCase())}
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                required
                maxLength={20}
                placeholder="yourname"
                aria-label="Username"
                aria-invalid={status === "invalid" || status === "reserved" || status === "taken"}
                className="w-full bg-transparent font-mono text-2xl tracking-tight outline-none placeholder:text-muted-foreground/50 md:text-3xl"
              />
              {status === "checking" ? (
                <span className="mb-1 shrink-0">
                  <Orb state="searching" size={20} aria-label="Checking username…" />
                </span>
              ) : null}
            </div>
            <StatusLine status={status} empty={!username.trim()} />
          </label>

          <label className="grid gap-1.5">
            <span className="micro">Display name</span>
            <Input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Optional nickname"
              maxLength={32}
            />
          </label>

          <label className="grid gap-1.5">
            <span className="micro">Email</span>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Optional · stays on this device"
              maxLength={120}
            />
          </label>

          <div className="flex flex-wrap items-center gap-4">
            <Button type="submit" disabled={!canSubmit}>
              {busy ? "Claiming…" : "Claim name"}
            </Button>
            <p className="text-xs text-muted-foreground">
              By claiming, you accept the{" "}
              <Link to="/terms" className="text-primary underline-offset-4 hover:underline">
                Terms
              </Link>
              . A name is a license, not property.
            </p>
          </div>
        </form>
      </Section>
    </PageEnter>
  );
}

function StatusLine({ status, empty }: { status: Status; empty: boolean }) {
  if (empty || status === "idle") {
    return (
      <p className="text-xs text-muted-foreground">
        3–20 characters. Start with a letter. a–z, 0–9, underscore.
      </p>
    );
  }
  if (status === "checking") {
    return <p className="text-xs text-muted-foreground">Checking…</p>;
  }
  if (status === "ok") {
    return <p className="text-xs text-primary">{reasonMessage("ok")}</p>;
  }
  return <p className="text-xs text-destructive">{reasonMessage(status)}</p>;
}

import { ThinkingOrb, type ThinkingOrbProps } from "thinking-orbs";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Host wrapper: auto theme, no mount when the user prefers reduced motion. */
export function Orb({
  state = "working",
  size = 64,
  theme = "auto",
  className,
  ...rest
}: ThinkingOrbProps) {
  const reduce = useReducedMotion();
  if (reduce) {
    const dot = size === 20 ? 6 : 10;
    return (
      <span
        className={cn("inline-block shrink-0 rounded-full bg-foreground/45", className)}
        style={{ width: dot, height: dot }}
        role="img"
        aria-label={rest["aria-label"] ?? state}
      />
    );
  }
  return <ThinkingOrb state={state} size={size} theme={theme} className={className} {...rest} />;
}

export function BoardLoading({ label = "Loading the board…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg px-4 py-16 ring-1 ring-border">
      <Orb state="searching" size={64} aria-label={label} />
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function CheckInButton({
  checkedIn,
  onCheckIn,
}: {
  checkedIn: boolean;
  onCheckIn: () => void;
}) {
  const [listening, setListening] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current != null) window.clearTimeout(timer.current);
    };
  }, []);

  const click = () => {
    if (checkedIn || listening) return;
    setListening(true);
    timer.current = window.setTimeout(() => {
      onCheckIn();
      setListening(false);
      timer.current = null;
    }, 720);
  };

  return (
    <Button type="button" disabled={checkedIn || listening} onClick={click}>
      {listening ? (
        <span className="inline-flex items-center gap-2">
          <Orb state="listening" size={20} aria-label="Checking in…" />
          Checking in…
        </span>
      ) : checkedIn ? (
        "Checked in"
      ) : (
        "I'm here today"
      )}
    </Button>
  );
}

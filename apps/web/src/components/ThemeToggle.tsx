import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  applyTheme,
  cycleTheme,
  readTheme,
  resolveTheme,
  writeTheme,
  type ThemePref,
} from "@/lib/theme";

export function ThemeToggle() {
  const [pref, setPref] = useState<ThemePref>(() =>
    typeof localStorage === "undefined" ? "system" : readTheme(),
  );
  const resolved = resolveTheme(pref);

  useEffect(() => {
    applyTheme(pref);
    if (pref !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [pref]);

  const onClick = () => {
    const next = cycleTheme(pref);
    writeTheme(next);
    applyTheme(next);
    setPref(next);
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={onClick}
      aria-label={`Theme ${pref}`}
      title={`Theme: ${pref}`}
    >
      {resolved === "dark" ? <Moon /> : <Sun />}
    </Button>
  );
}

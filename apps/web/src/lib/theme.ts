export const THEME_KEY = "0pening.theme";

export type ThemePref = "light" | "dark" | "system";

const PREFS: ThemePref[] = ["light", "dark", "system"];

export function isThemePref(value: unknown): value is ThemePref {
  return value === "light" || value === "dark" || value === "system";
}

export function readTheme(): ThemePref {
  try {
    const raw = localStorage.getItem(THEME_KEY);
    if (isThemePref(raw)) return raw;
  } catch {
    /* private mode */
  }
  return "system";
}

export function writeTheme(pref: ThemePref): void {
  try {
    localStorage.setItem(THEME_KEY, pref);
  } catch {
    /* private mode */
  }
}

export function systemDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(pref: ThemePref = readTheme()): "light" | "dark" {
  if (pref === "light" || pref === "dark") return pref;
  return systemDark() ? "dark" : "light";
}

export function applyTheme(pref: ThemePref = readTheme()): "light" | "dark" {
  const resolved = resolveTheme(pref);
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", resolved === "dark" ? "#000000" : "#f5f5f7");
  return resolved;
}

export function cycleTheme(pref: ThemePref): ThemePref {
  return PREFS[(PREFS.indexOf(pref) + 1) % PREFS.length];
}

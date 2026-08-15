export function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatCompact(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) {
    const v = n / 1_000_000;
    return `${v >= 10 ? v.toFixed(1) : v.toFixed(2)}M`;
  }
  if (abs >= 1_000) {
    const v = n / 1_000;
    return `${v >= 100 ? Math.round(v) : v.toFixed(1)}k`;
  }
  return formatCount(n);
}

export function formatPercent(n: number): string {
  if (!Number.isFinite(n)) return "—";
  const pct = n * 100;
  if (pct >= 10) return `${pct.toFixed(0)}%`;
  return `${pct.toFixed(1)}%`;
}

export function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  const a = parts[0]?.[0] || "?";
  const b = parts.length > 1 ? parts[parts.length - 1][0] : parts[0]?.[1] || "";
  return (a + b).toUpperCase();
}

export function formatPercentPoints(n: number): string {
  if (!Number.isFinite(n)) return "—";
  if (n >= 10) return `${n.toFixed(0)}%`;
  return `${n.toFixed(1)}%`;
}

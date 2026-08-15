import { Card, CardContent } from "@/components/ui/card";
import { CountUp } from "./CountUp";

export function KpiCard({
  label,
  value,
  hint,
  count,
  format,
}: {
  label: string;
  value: string;
  hint?: string;
  count?: number;
  format?: (n: number) => string;
}) {
  return (
    <Card size="sm" className="lift bg-card">
      <CardContent className="pt-1">
        <div className="micro">{label}</div>
        <div className="mt-2 font-mono text-[2rem] leading-none tracking-tight tabular-nums">
          {count != null ? <CountUp value={count} format={format} duration={0.4} /> : value}
        </div>
        {hint ? <div className="mt-2 text-xs text-muted-foreground">{hint}</div> : null}
      </CardContent>
    </Card>
  );
}

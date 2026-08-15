import { Card, CardContent } from "@/components/ui/card";

export function KpiCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card size="sm" className="lift bg-card">
      <CardContent className="pt-1">
        <div className="micro">{label}</div>
        <div className="mt-2 font-mono text-[2rem] leading-none tracking-tight tabular-nums">
          {value}
        </div>
        {hint ? <div className="mt-2 text-xs text-muted-foreground">{hint}</div> : null}
      </CardContent>
    </Card>
  );
}

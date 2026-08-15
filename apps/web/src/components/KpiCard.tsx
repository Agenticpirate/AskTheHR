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
    <Card size="sm" className="bg-card/80">
      <CardContent className="pt-1">
        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </div>
        <div className="font-heading mt-2 text-[2rem] leading-none tracking-tight">{value}</div>
        {hint ? <div className="mt-2 text-xs text-muted-foreground">{hint}</div> : null}
      </CardContent>
    </Card>
  );
}

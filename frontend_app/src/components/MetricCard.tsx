import { SparklineChart } from "./SparklineChart";

interface MetricCardProps {
  label: string;
  value: string | number;
  unit: string;
  sparkData: number[];
  sparkColor?: string;
}

export function MetricCard({ label, value, unit, sparkData, sparkColor = "hsl(160,60%,45%)" }: MetricCardProps) {
  return (
    <div className="card-gradient rounded-lg border border-border p-4 glow-border transition-all hover:border-primary/30">
      <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">{label}</p>
      <div className="flex items-end justify-between">
        <div>
          <span className="text-2xl font-semibold font-mono text-foreground">{value}</span>
          <span className="text-xs text-muted-foreground ml-1">{unit}</span>
        </div>
        <SparklineChart data={sparkData} color={sparkColor} />
      </div>
    </div>
  );
}

import { useMemo } from "react";

interface SparklineChartProps {
  data: number[];
  color?: string;
  height?: number;
  width?: number;
}

export function SparklineChart({ data, color = "hsl(160,60%,45%)", height = 32, width = 120 }: SparklineChartProps) {
  const path = useMemo(() => {
    if (data.length < 2) return "";
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const stepX = width / (data.length - 1);
    const points = data.map((v, i) => ({
      x: i * stepX,
      y: height - ((v - min) / range) * (height - 4) - 2,
    }));
    let d = `M${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      const cp1x = points[i - 1].x + stepX / 3;
      const cp1y = points[i - 1].y;
      const cp2x = points[i].x - stepX / 3;
      const cp2y = points[i].y;
      d += ` C${cp1x},${cp1y} ${cp2x},${cp2y} ${points[i].x},${points[i].y}`;
    }
    return d;
  }, [data, height, width]);

  return (
    <svg width={width} height={height} className="sparkline-fade">
      <defs>
        <linearGradient id={`grad-${color.replace(/[^a-z0-9]/gi, "")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={path} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" />
    </svg>
  );
}

import { useState, useEffect, useCallback } from "react";

function randomInRange(min: number, max: number) {
  return Math.round((Math.random() * (max - min) + min) * 10) / 10;
}

function generateHistoricalData(points: number, min: number, max: number, smooth = true) {
  const data: { time: string; value: number }[] = [];
  let prev = randomInRange(min, max);
  const now = Date.now();
  for (let i = points; i >= 0; i--) {
    const t = new Date(now - i * 60000);
    const timeStr = t.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    if (smooth) {
      prev = Math.max(min, Math.min(max, prev + randomInRange(-3, 3)));
    } else {
      prev = randomInRange(min, max);
    }
    data.push({ time: timeStr, value: Math.round(prev) });
  }
  return data;
}

export function useMockData() {
  const [heartRate, setHeartRate] = useState(72);
  const [gsr, setGsr] = useState(450);
  const [activity, setActivity] = useState(0.3);
  const [hrHistory, setHrHistory] = useState(() => generateHistoricalData(10, 65, 90));
  const [gsrHistory, setGsrHistory] = useState(() => generateHistoricalData(10, 380, 520));
  const [hrSparkline, setHrSparkline] = useState(() =>
    Array.from({ length: 20 }, () => randomInRange(68, 82))
  );
  const [gsrSparkline, setGsrSparkline] = useState(() =>
    Array.from({ length: 20 }, () => randomInRange(420, 480))
  );
  const [actSparkline, setActSparkline] = useState(() =>
    Array.from({ length: 20 }, () => randomInRange(0.1, 0.6))
  );

  const tick = useCallback(() => {
    setHeartRate((p) => Math.max(60, Math.min(110, p + randomInRange(-2, 2))));
    setGsr((p) => Math.max(350, Math.min(550, p + randomInRange(-8, 8))));
    setActivity((p) => Math.max(0, Math.min(1, +(p + randomInRange(-0.05, 0.05)).toFixed(2))));
    setHrSparkline((p) => [...p.slice(1), randomInRange(68, 82)]);
    setGsrSparkline((p) => [...p.slice(1), randomInRange(420, 480)]);
    setActSparkline((p) => [...p.slice(1), randomInRange(0.1, 0.6)]);
  }, []);

  useEffect(() => {
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, [tick]);

  return {
    heartRate: Math.round(heartRate),
    gsr: Math.round(gsr),
    activity,
    hrHistory,
    gsrHistory,
    hrSparkline,
    gsrSparkline,
    actSparkline,
  };
}

import { Loader2, ChevronDown, Circle } from "lucide-react";
import { useState, useEffect } from "react";
import { MetricCard } from "@/components/MetricCard";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const users = ["Subject A — Primary", "Subject B — Control", "Subject C — Trial"];

// Helper to get current timestamp for the chart
const getTime = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

export default function LiveDashboard() {
  const [selectedUser, setSelectedUser] = useState(users[0]);
  const [userOpen, setUserOpen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  
  // Real Data State
  const [biometrics, setBiometrics] = useState({
    heart_rate: 0,
    gsr: 0,
    emotion_state: "WAITING...",
    activity: 0
  });

  // History State for the Charts
  const [hrHistory, setHrHistory] = useState<{time: string, value: number}[]>([]);
  const [gsrHistory, setGsrHistory] = useState<{time: string, value: number}[]>([]);

  // POLLING LOGIC: This reads the JSON file Python is writing
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetching from the public folder where Python saves the data
        const response = await fetch("/data/live_biometrics.json");
        if (!response.ok) throw new Error("Backend not found");
        
        const newData = await response.json();
        setBiometrics(newData);
        setIsConnected(true);

        // Update the Charts (Keep the last 20 data points)
        const timestamp = getTime();
        setHrHistory(prev => [...prev.slice(-19), { time: timestamp, value: newData.heart_rate }]);
        setGsrHistory(prev => [...prev.slice(-19), { time: timestamp, value: newData.gsr }]);

      } catch (error) {
        setIsConnected(false);
        console.error("Dashboard Polling Error:", error);
      }
    };

    const interval = setInterval(fetchData, 1000); // Update every 1 second
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground tracking-tight flex items-center gap-2">
            Live Dashboard 
            <Circle className={`h-2.5 w-2.5 fill-current ${isConnected ? 'text-green-500 animate-pulse' : 'text-red-500'}`} />
          </h1>
          <p className="text-sm text-muted-foreground">
            {isConnected ? "Connected to IKIMONO Brain" : "Searching for Backend..."}
          </p>
        </div>
        
        {/* User Selector */}
        <div className="relative">
          <button
            onClick={() => setUserOpen(!userOpen)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground hover:border-primary/40 transition-colors"
          >
            {selectedUser}
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          {userOpen && (
            <div className="absolute right-0 mt-1 w-56 rounded-lg border border-border bg-card shadow-lg z-10">
              {users.map((u) => (
                <button
                  key={u}
                  onClick={() => { setSelectedUser(u); setUserOpen(false); }}
                  className="block w-full text-left px-3 py-2 text-sm text-foreground hover:bg-accent transition-colors first:rounded-t-lg last:rounded-b-lg"
                >
                  {u}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Primary Emotion Status */}
      <div className="card-gradient rounded-xl border border-border p-8 glow-border text-center relative overflow-hidden">
        <p className="text-xs text-muted-foreground uppercase tracking-[0.25em] mb-2">Current Emotion State</p>
        <h2 className={`text-6xl font-bold font-mono tracking-tight animate-pulse-glow ${
          biometrics.emotion_state === 'STRESSED' ? 'text-red-500' : 'text-emotion-calm'
        }`}>
          {biometrics.emotion_state}
        </h2>
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* Metric Cards - Linked to Real Data */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard 
          label="Heart Rate" 
          value={biometrics.heart_rate} 
          unit="BPM" 
          sparkData={hrHistory.map(d => d.value)} 
          sparkColor="hsl(160,60%,50%)" 
        />
        <MetricCard 
          label="GSR (Skin Conductance)" 
          value={biometrics.gsr} 
          unit="µS" 
          sparkData={gsrHistory.map(d => d.value)} 
          sparkColor="hsl(270,60%,60%)" 
        />
        <MetricCard 
          label="Activity Level" 
          value={biometrics.activity.toFixed(2)} 
          unit="g" 
          sparkData={[0, 0, 0]} 
          sparkColor="hsl(45,90%,55%)" 
        />
      </div>

      {/* Real-time Charts */}
      <div className="space-y-4">
        <ChartCard title="Live Heart Rate (BPM)" data={hrHistory} color="hsl(160,60%,50%)" yDomain={[40, 120]} />
        <ChartCard title="Live GSR (µS)" data={gsrHistory} color="hsl(270,60%,60%)" yDomain={[100, 800]} />
      </div>
    </div>
  );
}

function ChartCard({ title, data, color, yDomain }: {
  title: string;
  data: { time: string; value: number }[];
  color: string;
  yDomain: [number, number];
}) {
  return (
    <div className="card-gradient rounded-xl border border-border p-5 glow-border">
      <p className="text-xs text-muted-foreground uppercase tracking-widest mb-4">{title}</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,16%)" vertical={false} />
          <XAxis dataKey="time" tick={{ fill: "hsl(215,15%,50%)", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis domain={yDomain} tick={{ fill: "hsl(215,15%,50%)", fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(220,18%,10%)",
              border: "1px solid hsl(220,14%,16%)",
              borderRadius: "8px",
            }}
          />
          <Line isAnimationActive={false} type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
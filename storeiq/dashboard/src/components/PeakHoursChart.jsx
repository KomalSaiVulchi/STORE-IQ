import {
  AreaChart,
  Area,
  ResponsiveContainer,
  XAxis,
  Tooltip,
} from "recharts";

export default function PeakHoursChart({ peakHours = [] }) {
  const data = peakHours.length
    ? peakHours
    : [{ hour: "--:--", visitors: 0 }];

  return (
    <div className="bg-slate/80 border border-white/10 rounded-2xl p-5">
      <div className="text-lg font-display">Peak Hours</div>
      <div className="text-xs text-white/60 mt-1">Hourly unique visitors</div>
      <div className="h-56 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <XAxis dataKey="hour" tick={{ fontSize: 10 }} />
            <Tooltip />
            <Area
              type="monotone"
              dataKey="visitors"
              stroke="#22d3ee"
              fill="#22d3ee"
              fillOpacity={0.2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

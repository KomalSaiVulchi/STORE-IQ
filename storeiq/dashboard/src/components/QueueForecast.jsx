import {
  LineChart,
  Line,
  XAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function QueueForecast({ queueForecast = {} }) {
  const current = Number(queueForecast.current_queue || 0);
  const forecast10 = Number(queueForecast.forecast_10min || 0);
  const forecast30 = Number(queueForecast.forecast_30min || 0);
  const confidence = Number(queueForecast.confidence || 0);
  const recommendation = queueForecast.recommendation || "Queue levels stable — continue monitoring";

  const data = [
    { label: "Now", value: current },
    { label: "+10m", value: forecast10 },
    { label: "+30m", value: forecast30 },
  ];

  return (
    <div className="bg-slate/80 border border-white/10 rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-display">Queue Forecast</div>
          <div className="text-xs text-white/60">Exponential smoothing</div>
        </div>
        <div className="text-xs text-aurora">Confidence {confidence.toFixed(2)}</div>
      </div>
      <div className="h-48 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="label" />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#ff6b3d" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="text-sm text-white/70">Recommendation: {recommendation}</div>
    </div>
  );
}

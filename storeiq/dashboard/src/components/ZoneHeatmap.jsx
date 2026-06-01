import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const colorFor = (score) => {
  if (score > 70) return "#22c55e";
  if (score > 40) return "#fbbf24";
  return "#ff6b3d";
};

export default function ZoneHeatmap({ metrics }) {
  const scores = metrics.zone_scores || {};
  const data = Object.keys(scores).map((key) => ({
    zone: key,
    score: scores[key],
  }));

  return (
    <div className="bg-slate/80 border border-white/10 rounded-2xl p-5">
      <div className="text-lg font-display">Zone Heatmap</div>
      <div className="h-56 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 10 }}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="zone" width={90} />
            <Tooltip />
            <Bar dataKey="score" radius={[8, 8, 8, 8]}>
              {data.map((entry) => (
                <Cell key={entry.zone} fill={colorFor(entry.score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

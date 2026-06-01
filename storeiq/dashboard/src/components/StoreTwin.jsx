const ZONES = [
  { id: "ENTRANCE", x: 20, y: 20, w: 160, h: 120 },
  { id: "SKINCARE", x: 200, y: 20, w: 180, h: 120 },
  { id: "MAKEUP", x: 400, y: 20, w: 180, h: 120 },
  { id: "HAIRCARE", x: 20, y: 170, w: 160, h: 140 },
  { id: "BILLING", x: 200, y: 170, w: 180, h: 140 },
];

const fillFor = (score) => {
  if (score > 70) return "#22c55e";
  if (score > 40) return "#fbbf24";
  return "#ff6b3d";
};

export default function StoreTwin({ metrics }) {
  const scores = metrics.zone_scores || {};

  return (
    <div className="bg-slate/80 border border-white/10 rounded-2xl p-5">
      <div className="text-lg font-display">Store Digital Twin</div>
      <svg viewBox="0 0 600 340" className="w-full h-56 mt-4">
        <rect x="0" y="0" width="600" height="340" fill="#0b1220" rx="20" />
        {ZONES.map((zone) => (
          <g key={zone.id}>
            <rect
              x={zone.x}
              y={zone.y}
              width={zone.w}
              height={zone.h}
              rx="12"
              fill={fillFor(scores[zone.id] || 0)}
              opacity="0.7"
            />
            <text
              x={zone.x + 12}
              y={zone.y + 24}
              fill="#fff"
              fontSize="12"
              fontFamily="IBM Plex Sans"
            >
              {zone.id}
            </text>
            <circle
              cx={zone.x + zone.w - 16}
              cy={zone.y + 16}
              r="10"
              fill="#0f172a"
              className={scores[zone.id] < 40 ? "pulse" : ""}
            />
            <text
              x={zone.x + zone.w - 20}
              y={zone.y + 20}
              fill="#fff"
              fontSize="10"
            >
              {Math.max(1, Math.round((scores[zone.id] || 0) / 10))}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function AnomalyFeed({ anomalies = [] }) {
  const list = anomalies.filter(Boolean);

  return (
    <div className="bg-slate/80 border border-white/10 rounded-2xl p-5">
      <div className="text-lg font-display">Active Anomalies</div>
      <div className="mt-4 space-y-3">
        {list.length === 0 && (
          <div className="text-sm text-white/50 p-3 rounded-xl border border-white/10">
            No active anomalies — store operating normally.
          </div>
        )}
        {list.map((item, index) => (
          <div
            key={`${item.type}-${item.anomaly_id || index}`}
            className={`p-3 rounded-xl border ${
              item.severity === "CRITICAL"
                ? "border-ember/60 bg-ember/10"
                : "border-gold/60 bg-gold/10"
            }`}
          >
            <div className="flex items-center justify-between text-xs uppercase">
              <span>{item.type}</span>
              <span>{item.severity}</span>
            </div>
            <div className="mt-2 text-sm">{item.reason}</div>
            {item.suggested_action && (
              <div className="mt-2 text-xs text-white/70">{item.suggested_action}</div>
            )}
            <div className="mt-2 text-xs text-white/60">
              Confidence {Number(item.confidence || 0).toFixed(2)}
              {item.timestamp ? ` · ${item.timestamp}` : ""}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

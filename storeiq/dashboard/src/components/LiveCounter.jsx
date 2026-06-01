export default function LiveCounter({ metrics }) {
  const cards = [
    { label: "Current Visitors", value: metrics.current_in_store },
    { label: "Avg Dwell", value: `${metrics.avg_dwell_minutes} min` },
    { label: "Conversion Rate", value: `${metrics.conversion_rate}%` },
    { label: "Queue Depth", value: metrics.queue_depth },
  ];

  return (
    <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-slate/80 border border-white/10 rounded-2xl p-5 card-glow"
        >
          <div className="text-sm text-white/60">{card.label}</div>
          <div className="mt-2 text-3xl font-display font-semibold">
            {card.value}
          </div>
        </div>
      ))}
    </section>
  );
}

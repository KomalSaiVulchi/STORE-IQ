import {
  FunnelChart as ReFunnelChart,
  Funnel,
  Tooltip,
  LabelList,
  ResponsiveContainer,
} from "recharts";

export default function FunnelChart({ funnel = [], funnelAlert = "" }) {
  const data = funnel.length
    ? funnel.map((stage) => ({
        stage: stage.stage,
        count: stage.count,
        pct: stage.pct,
      }))
    : [{ stage: "ENTRY", count: 0, pct: 0 }];

  const billingPct = data.find((s) => s.stage === "BILLING")?.pct || 0;
  const purchasePct = data.find((s) => s.stage === "PURCHASE")?.pct || 0;
  const dropOff = billingPct - purchasePct;

  return (
    <div className="bg-slate/80 border border-white/10 rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-display">Live Funnel</div>
          <div className="text-xs text-white/60">Entry → Purchase</div>
        </div>
        {dropOff > 50 && (
          <span className="text-xs bg-ember/20 text-ember px-3 py-1 rounded-full">
            Drop-off alert
          </span>
        )}
      </div>
      {funnelAlert && (
        <div className="text-xs text-gold mt-2">{funnelAlert}</div>
      )}
      <div className="h-56 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <ReFunnelChart>
            <Tooltip />
            <Funnel dataKey="count" data={data} isAnimationActive>
              <LabelList position="right" fill="#fff" dataKey="stage" />
            </Funnel>
          </ReFunnelChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

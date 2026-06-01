import { useState } from "react";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import LiveCounter from "./components/LiveCounter.jsx";
import FunnelChart from "./components/FunnelChart.jsx";
import ZoneHeatmap from "./components/ZoneHeatmap.jsx";
import AnomalyFeed from "./components/AnomalyFeed.jsx";
import PeakHoursChart from "./components/PeakHoursChart.jsx";
import QueueForecast from "./components/QueueForecast.jsx";
import StoreTwin from "./components/StoreTwin.jsx";
import useStoreSocket from "./hooks/useStoreSocket.js";

const CONNECTION_STYLES = {
  live: { dot: "bg-moss", label: "WebSocket live" },
  reconnecting: { dot: "bg-gold animate-pulse", label: "Reconnecting..." },
  error: { dot: "bg-red-500", label: "Connection error" },
  disconnected: { dot: "bg-gray-500", label: "Disconnected" },
};

export default function App() {
  const state = useStoreSocket();
  const [active, setActive] = useState("Dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navItems = ["Dashboard", "Analytics", "Anomalies", "Settings"];
  const conn = CONNECTION_STYLES[state.connection] || CONNECTION_STYLES.disconnected;

  return (
    <div className="min-h-screen text-white">
      {/* Mobile header */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b border-white/10">
        <div className="text-xl font-display font-semibold">StoreIQ</div>
        <button
          type="button"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition"
          aria-label="Toggle menu"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      <div className="flex">
        {/* Sidebar — responsive */}
        <aside
          className={`${
            sidebarOpen ? "block" : "hidden"
          } lg:block w-64 bg-slate/80 border-r border-white/10 p-6 fixed lg:sticky top-0 h-screen z-50`}
        >
          <div className="text-2xl font-display font-semibold tracking-tight">
            StoreIQ
          </div>
          <div className="text-sm text-white/60 mt-2">Purplle Store Intelligence</div>
          <nav className="mt-10 space-y-2 text-white/80">
            {navItems.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => {
                  setActive(item);
                  setSidebarOpen(false);
                }}
                className={`w-full text-left px-3 py-2 rounded-xl transition ${
                  active === item ? "bg-white/10 text-white" : "hover:bg-white/5"
                }`}
                aria-pressed={active === item}
              >
                {item}
              </button>
            ))}
          </nav>
          <div className="mt-10 text-xs flex items-center">
            <span className={`inline-block w-2 h-2 rounded-full mr-2 ${conn.dot}`}></span>
            {conn.label}
          </div>
          <div className="mt-2 text-xs text-white/30">v1.0.0</div>
        </aside>

        {/* Overlay for mobile sidebar */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <main className="flex-1 p-4 lg:p-10 space-y-6">
          {active === "Dashboard" && (
            <>
              <ErrorBoundary>
                <LiveCounter metrics={state.metrics} />
              </ErrorBoundary>
              <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <ErrorBoundary>
                  <FunnelChart funnel={state.funnel} funnelAlert={state.funnelAlert} />
                </ErrorBoundary>
                <ErrorBoundary>
                  <ZoneHeatmap metrics={state.metrics} />
                </ErrorBoundary>
              </section>
              <section className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <ErrorBoundary>
                  <StoreTwin metrics={state.metrics} />
                </ErrorBoundary>
                <ErrorBoundary>
                  <PeakHoursChart peakHours={state.peakHours} />
                </ErrorBoundary>
                <ErrorBoundary>
                  <AnomalyFeed anomalies={state.anomalies} />
                </ErrorBoundary>
              </section>
              <section className="grid grid-cols-1">
                <ErrorBoundary>
                  <QueueForecast queueForecast={state.queueForecast} />
                </ErrorBoundary>
              </section>
            </>
          )}

          {active === "Analytics" && (
            <>
              <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <ErrorBoundary>
                  <FunnelChart funnel={state.funnel} funnelAlert={state.funnelAlert} />
                </ErrorBoundary>
                <ErrorBoundary>
                  <ZoneHeatmap metrics={state.metrics} />
                </ErrorBoundary>
              </section>
              <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <ErrorBoundary>
                  <PeakHoursChart peakHours={state.peakHours} />
                </ErrorBoundary>
                <ErrorBoundary>
                  <QueueForecast queueForecast={state.queueForecast} />
                </ErrorBoundary>
              </section>
            </>
          )}

          {active === "Anomalies" && (
            <section className="grid grid-cols-1">
              <ErrorBoundary>
                <AnomalyFeed anomalies={state.anomalies} />
              </ErrorBoundary>
            </section>
          )}

          {active === "Settings" && (
            <section className="bg-slate/80 border border-white/10 rounded-2xl p-5">
              <div className="text-lg font-display">Settings</div>
              <div className="text-sm text-white/60 mt-2">
                Coming soon: per-store thresholds, camera adjacency, and alert routing.
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

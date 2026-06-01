import { useCallback, useEffect, useRef, useState } from "react";

const STORE_ID = "STORE_BLR_002";

const DEFAULT_STATE = {
  metrics: {
    unique_visitors: 0,
    current_in_store: 0,
    avg_dwell_minutes: 0,
    conversion_rate: 0,
    queue_depth: 0,
    peak_hour: "--:--",
    zone_scores: {},
  },
  funnel: [],
  funnelAlert: "",
  peakHours: [],
  anomalies: [],
  queueForecast: {
    current_queue: 0,
    forecast_10min: 0,
    forecast_30min: 0,
    confidence: 0,
    recommendation: "Waiting for live data...",
  },
  connection: "disconnected",
};

const MAX_RECONNECT_DELAY = 30000;
const INITIAL_RECONNECT_DELAY = 1000;

function getApiBaseUrl() {
  if (typeof window === "undefined") return "http://localhost:8000";
  const { protocol, hostname, port } = window.location;
  if (import.meta.env?.DEV) {
    return `${protocol}//${hostname}:8000`;
  }
  if (port === "3000" || port === "80" || port === "") {
    return `${protocol}//${hostname}${port ? `:${port}` : ""}/api`;
  }
  return `${protocol}//${hostname}:8000`;
}

function getWebSocketUrl() {
  if (typeof window === "undefined") return "ws://localhost:8000/ws/live";

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const { hostname, port } = window.location;

  if (port === "3000" || port === "80" || port === "") {
    const wsPort = port || (protocol === "wss:" ? "443" : "80");
    return `${protocol}//${hostname}:${wsPort}/ws/live`;
  }

  return `${protocol}//${hostname}:8000/ws/live`;
}

function applyPayload(payload, prev) {
  const metrics = payload.metrics || {};
  return {
    ...prev,
    anomalies: payload.anomalies || [],
    funnel: payload.funnel || [],
    funnelAlert: payload.funnel_alert || "",
    peakHours: payload.peak_hours || [],
    queueForecast: payload.queue_forecast || prev.queueForecast,
    metrics: {
      unique_visitors: Number(metrics.unique_visitors || 0),
      current_in_store: Number(metrics.current_in_store || 0),
      avg_dwell_minutes: Number(metrics.avg_dwell_minutes || 0),
      conversion_rate: Number(metrics.conversion_rate || 0),
      queue_depth: Number(metrics.queue_depth || 0),
      peak_hour: metrics.peak_hour || "--:--",
      zone_scores: metrics.zone_scores || {},
    },
  };
}

export default function useStoreSocket() {
  const [state, setState] = useState(DEFAULT_STATE);
  const socketRef = useRef(null);
  const reconnectDelayRef = useRef(INITIAL_RECONNECT_DELAY);
  const reconnectTimerRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchSnapshot = useCallback(async () => {
    try {
      const base = getApiBaseUrl();
      const [metricsRes, funnelRes, heatmapRes, anomaliesRes, queueRes] = await Promise.all([
        fetch(`${base}/stores/${STORE_ID}/metrics`),
        fetch(`${base}/stores/${STORE_ID}/funnel`),
        fetch(`${base}/stores/${STORE_ID}/heatmap`),
        fetch(`${base}/stores/${STORE_ID}/anomalies?active_only=true`),
        fetch(`${base}/stores/${STORE_ID}/predict/queue`),
      ]);

      const metrics = metricsRes.ok ? await metricsRes.json() : {};
      const funnelData = funnelRes.ok ? await funnelRes.json() : {};
      const heatmap = heatmapRes.ok ? await heatmapRes.json() : {};
      const anomaliesData = anomaliesRes.ok ? await anomaliesRes.json() : {};
      const queueForecast = queueRes.ok ? await queueRes.json() : DEFAULT_STATE.queueForecast;

      if (!mountedRef.current) return;

      setState((prev) =>
        applyPayload(
          {
            metrics: {
              ...metrics,
              zone_scores: heatmap.zones || metrics.zone_scores || {},
            },
            funnel: funnelData.stages || [],
            funnel_alert: funnelData.drop_off_alert || "",
            peak_hours: prev.peakHours,
            queue_forecast: queueForecast,
            anomalies: (anomaliesData.anomalies || []).map((item) => ({
              ...item,
              timestamp: item.created_at ? new Date(item.created_at).toLocaleTimeString() : "recent",
            })),
          },
          prev
        )
      );
    } catch (err) {
      console.warn("StoreIQ: REST snapshot fetch failed", err);
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const url = getWebSocketUrl();
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      if (!mountedRef.current) return;
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY;
      setState((prev) => ({ ...prev, connection: "live" }));
    };

    socket.onclose = () => {
      if (!mountedRef.current) return;
      setState((prev) => ({ ...prev, connection: "reconnecting" }));
      const delay = reconnectDelayRef.current;
      reconnectTimerRef.current = setTimeout(() => {
        reconnectDelayRef.current = Math.min(
          MAX_RECONNECT_DELAY,
          reconnectDelayRef.current * 2 + Math.random() * 500
        );
        connect();
      }, delay);
    };

    socket.onerror = () => {
      if (!mountedRef.current) return;
      setState((prev) => ({ ...prev, connection: "error" }));
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setState((prev) => applyPayload(payload, prev));
      } catch (err) {
        console.warn("StoreIQ: Failed to parse WebSocket message", err);
      }
    };

    const ping = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 2000);

    socket._pingInterval = ping;
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    fetchSnapshot();
    connect();

    const poll = setInterval(fetchSnapshot, 15000);

    return () => {
      mountedRef.current = false;
      clearInterval(poll);
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (socketRef.current) {
        if (socketRef.current._pingInterval) {
          clearInterval(socketRef.current._pingInterval);
        }
        socketRef.current.close();
      }
    };
  }, [connect, fetchSnapshot]);

  return state;
}

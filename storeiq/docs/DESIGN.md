# Design RFC: Purplle StoreIQ

## Problem Statement
Purplle requires a real-time, multi-camera Store Intelligence platform to track visitors, compute conversion funnels, detect anomalies, and forecast queues across 40 stores without impacting in-store latency. The system must process CCTV footage to generate actionable insights for store managers and regional directors, including visitor counts, dwell times, queue depths, and heatmaps.

## Constraints
- **Latency:** End-to-end latency under 500ms per frame to ensure real-time responsiveness.
- **Accuracy:** Multi-camera re-identification across adjacent cameras with high precision.
- **Robustness:** Accurate re-entry handling without double counting unique visitors.
- **Reliability:** High availability with replayable event streams to handle network partitions or downstream outages.

## Architecture Decisions
- **YOLOv11**: Chosen for fast person detection, offering a strong balance between accuracy and edge deployment performance.
- **ByteTrack**: Implemented for stable multi-object tracking. It handles occlusion better than SORT without the heavy computational overhead of DeepSORT's integrated ReID during the tracking phase.
- **OSNet (TorchReID)**: Utilized for lightweight ReID embeddings, enabling accurate cross-camera identity resolution while maintaining low latency.
- **Kafka**: Selected for durable event streaming, decoupling producers from consumers, and allowing independent scaling.
- **Redis**: Used for low-latency live dashboards, WebSocket state management, and feature TTL caches.
- **PostgreSQL**: Chosen for transactionally consistent session records and aggregated historical metrics.

## Data Flow
1. **Ingestion**: CCTV Camera Frames are fed into the system.
2. **Detection & Tracking**: YOLOv11 detects persons, ByteTrack maintains short-term trajectories, and OSNet extracts embeddings for cross-camera ReID.
3. **Zone Mapping**: Detected coordinates are mapped to logical store zones (e.g., ENTRANCE, SKINCARE, BILLING).
4. **Event Generation**: The system emits standardized events (ENTRY, ZONE_ENTER, BILLING_QUEUE_JOIN, etc.).
5. **Streaming**: Events are published to a Kafka `raw_events` topic.
6. **API Ingestion**: The FastAPI backend consumes these events and persists them to PostgreSQL.
7. **Analytics**: Asynchronous workers process the events to update sessions, detect anomalies, and compute metrics.

## Failure Scenarios
- **Kafka Unavailability**: The pipeline buffers events in-memory and retries; the API falls back to synchronous PostgreSQL writes if the producer fails.
- **Camera Offline**: Missing detections for > 10 minutes triggers a `CAMERA_OFFLINE` anomaly, alerting maintenance staff.
- **Database Outage**: The API degrades gracefully, returning 503 Service Unavailable, while the pipeline continues buffering to Kafka.

## Scaling Plan to 40 Stores
- **Database Partitioning**: Multi-tenant schema with `store_id` partitioning for efficient queries.
- **Message Broker**: Regional Kafka clusters per metro area to reduce latency and isolate failures.
- **Compute**: Horizontal scaling of pipeline workers per store, deployed via Kubernetes at the edge.
- **State Management**: Shared feature store keyed by `visitor_id` and `store_id`.

## AI-Assisted Decisions
1. **Multi-stage Ingestion**: Claude suggested separating the edge pipeline from the centralized API via Kafka, with schema validation at the edge. Accepted to enforce event shape and improve resilience.
2. **ReID Stack**: Claude initially suggested a deep CNN-only re-identification stack. Rejected due to edge latency constraints; opted for OSNet for its lightweight profile.
3. **Cache Architecture**: Claude proposed a complex multi-tier caching system. Rejected in favor of a simpler Redis + PostgreSQL approach to reduce operational complexity and maintenance overhead.

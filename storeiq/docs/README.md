# Purplle StoreIQ

Purplle StoreIQ is a production-grade, multi-camera AI Store Intelligence System designed for real-time store analytics, anomaly detection, and operational forecasting.

## System Overview

```
+-------------+     +--------------------+     +------------------+
|  RTSP/MP4   | --> |  AI Pipeline       | --> | Kafka Topics     |
|  Cameras    |     |  YOLOv11/ByteTrack |     | raw/sessions/anom|
+-------------+     |  OSNet ReID        |     +---------+--------+
                    +---------+----------+               |
                              |                          v
                              |                +------------------+
                              |                | FastAPI Backend  |
                              |                | PostgreSQL/Redis |
                              |                +---------+--------+
                              |                          |
                              v                          v
                      +---------------+         +-----------------+
                      | Feature Store |         | React Dashboard |
                      +---------------+         +-----------------+
```

## Quick Start

```bash
docker compose up --build
```

API: http://localhost:8000
Dashboard: http://localhost:3000
Docs: http://localhost:8000/docs

## Project Structure

```
storeiq/
├── detector/
├── pipeline/
├── streaming/
├── analytics/
├── anomaly/
├── feature_store/
├── api/
├── database/
├── dashboard/
├── docker/
├── docs/
└── tests/
```

## API Endpoints

### POST /events/ingest
```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "7b0a8a4c-0c1f-4d20-9bdb-8c3bb5a4c8b8",
    "event_type": "ENTRY",
    "visitor_id": "visitor-001",
    "camera_id": "cam_01",
    "zone_id": "ENTRANCE",
    "timestamp": "2026-05-29T10:23:11Z",
    "metadata": {"confidence": 0.91}
  }'
```

### GET /metrics
```bash
curl http://localhost:8000/metrics
```

### GET /funnel
```bash
curl http://localhost:8000/funnel
```

### GET /heatmap
```bash
curl http://localhost:8000/heatmap
```

### GET /anomalies
```bash
curl "http://localhost:8000/anomalies?active_only=true&severity=CRITICAL"
```

### GET /predict/queue
```bash
curl http://localhost:8000/predict/queue
```

### GET /health
```bash
curl http://localhost:8000/health
```

## Sample Event Payloads

```json
{
  "event_id": "c2f6b2e0-1e6a-4ef5-9306-2b5b233a8c1d",
  "event_type": "ZONE_ENTER",
  "visitor_id": "visitor-019",
  "camera_id": "cam_02",
  "zone_id": "SKINCARE",
  "timestamp": "2026-05-29T10:28:14Z",
  "metadata": {"track_id": 42}
}
```

## Running with a Sample Video

The pipeline defaults to a generated sample mp4 file if no RTSP stream is provided.

```bash
export SAMPLE_VIDEO_PATH=./pipeline/sample_video.mp4
export VIDEO_SOURCE=./pipeline/sample_video.mp4
```

Then run the pipeline container with Docker Compose (included in the default startup).

## Pretrained Weights

- YOLOv11 uses `yolo11n.pt` auto-downloaded by `ultralytics`.
- OSNet uses Market-1501 pretrained weights loaded via `torchreid`.
- ByteTrack is algorithmic and does not require weights.

## Seed Demo Data

```bash
docker compose exec api python -m database.seed
```

## Prometheus Metrics

Prometheus metrics are exposed at:

```
GET /metrics/prometheus
```

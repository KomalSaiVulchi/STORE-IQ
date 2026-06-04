StoreIQ

StoreIQ is a production-grade, multi-camera AI Store Intelligence System designed for real-time store analytics, anomaly detection, and operational forecasting.

**Store:** Brigade Bangalore (`STORE_BLR_002`)  
**Dashboard:** http://localhost:3000 (live metrics via WebSocket)  
**API:** http://localhost:8000  
**Docs:** http://localhost:8000/docs

## Quick Start (5 commands)

```bash
git clone https://github.com/KomalSaiVulchi/STORE-IQ.git
cd STORE-IQ/storeiq
cp .env.example .env
docker compose up --build
curl http://localhost:8000/stores/STORE_BLR_002/metrics
```

The API auto-loads POS transactions from `dataset/Brigade_Bangalore_10_April_26 (1)bc6219c.csv` on startup (mounted at `/app/dataset` in Docker).

## System Overview

```
+-------------+     +--------------------+     +------------------+
|  RTSP/MP4   | --> |  AI Pipeline       | --> | Kafka Topics     |
|  Cameras    |     |  YOLOv11/ByteTrack |     | raw/sessions/anom|
+-------------+     |  OSNet ReID        |     +---------+--------+
                    +---------+----------+               |
                              |                          v
                              |                +------------------+
                              |                | FastAPI Backend   |
                              |                | PostgreSQL/Redis  |
                              |                +---------+--------+
                              |                          |
                              v                          v
                      +---------------+         +-----------------+
                      | Feature Store |         | React Dashboard |
                      +---------------+         +-----------------+
```

## Project Structure

```
storeiq/
├── event_log.jsonl    # ⭐ DELIVERABLE — 2,426 events (JSONL)
├── detector/          # YOLOv11, ByteTrack, OSNet ReID
├── pipeline/          # Video ingestion, zone mapping, event generation
├── streaming/         # Kafka producer/consumer
├── analytics/         # Funnel, heatmap, prediction engines
├── anomaly/           # Anomaly detection
├── feature_store/     # Visitor feature persistence
├── api/               # FastAPI backend
├── database/          # SQLAlchemy models, migrations, seed
├── dashboard/         # React live dashboard (Part E bonus)
├── docker/            # Dockerfiles
├── dataset/           # POS CSV + store layout (CCTV videos excluded)
├── docs/
│   ├── DESIGN.md      # Architecture + AI-Assisted Decisions
│   ├── CHOICES.md     # Model, schema, and API trade-offs
│   └── SCORING.md     # Self-scoring rubric
└── tests/             # 51 unit/integration tests
```

## Dataset

Challenge reference data is bundled in the repo:

```
storeiq/dataset/
├── Brigade_Bangalore_10_April_26 (1)bc6219c.csv   # POS transactions
├── Brigade Road - Store layoutc5f5d56.xlsx         # Store layout
└── README.md                                       # Data documentation
```

> **Note:** CCTV video files (~650 MB) are excluded from the repo due to size. Place your CCTV clips in `dataset/CCTV Footage/` locally to run the detection pipeline. The API works without them using seed data.

Store layout is configured in `pipeline/store_layout.json` and zone polygons in `pipeline/zone_config.json`.

## Event Log (`event_log.jsonl`)

The primary deliverable — **2,426 events** in JSONL format following the `sample_events.jsonl` schema.

| Event Type | Count | Description |
|---|---|---|
| `entry` | 333 | Visitor enters store (CAM_ENTRY_01) |
| `exit` | 333 | Visitor exits store (CAM_ENTRY_01) |
| `zone_entered` | 821 | Visitor enters a zone (floor cameras) |
| `zone_exited` | 821 | Visitor exits a zone (floor cameras) |
| `queue_completed` | 105 | Visitor completes billing queue |
| `queue_abandoned` | 13 | Visitor abandons billing queue |

**Edge cases covered:**
- ✅ Staff exclusion (`is_staff: true` — 6 staff members)
- ✅ Re-entry detection (~5% visitors re-enter after exit)
- ✅ Group entry (`group_id` + `group_size` — ~15% arrive in groups of 2–4)
- ✅ Queue abandonment (~12% abandon rate)
- ✅ Face hidden (`is_face_hidden: true` — ~8%)
- ✅ Demographics (`gender_pred`, `age_pred`, `age_bucket`)

Generate a fresh event log:
```bash
python3 generate_event_log.py
```

## Running the Detection Pipeline

Process all 5 CCTV clips — events are persisted to PostgreSQL **and** published to Kafka (API consumer also ingests):

```bash
cd STORE-IQ/storeiq
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
./pipeline/run.sh
```

> **Prerequisite:** Place the CCTV footage files (`CAM 1.mp4` through `CAM 5.mp4`) in `dataset/CCTV Footage/` before running.

After processing, verify live data:

```bash
curl http://localhost:8000/stores/STORE_BLR_002/metrics
curl http://localhost:8000/stores/STORE_BLR_002/funnel
curl "http://localhost:8000/stores/STORE_BLR_002/anomalies?active_only=true"
```

The script maps each clip to its camera ID from `store_layout.json`:

| Clip     | Camera ID        | Coverage              |
|----------|------------------|-----------------------|
| CAM 1.mp4 | CAM_ENTRY_01    | Entry/Exit threshold  |
| CAM 2.mp4 | CAM_FLOOR_02    | Main floor zones      |
| CAM 3.mp4 | CAM_BILLING_03  | Billing counter       |
| CAM 4.mp4 | CAM_SKINCARE_04 | Skincare / fragrance  |
| CAM 5.mp4 | CAM_MAKEUP_05   | Makeup / personal care|

Events are published to Kafka (`raw_events`) and persisted to PostgreSQL. The API ingests the same events via `POST /events/ingest`.

### Load POS transactions manually

```bash
python -m pipeline.pos_loader "dataset/Brigade_Bangalore_10_April_26 (1)bc6219c.csv"
```

## API Endpoints

All store-scoped endpoints use `STORE_BLR_002` for the Brigade Bangalore store.

### POST /events/ingest
Accepts a single event, a batch object (`{"events": [...]}`), or a raw array (up to 500 events). Idempotent by `event_id`.

```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "7b0a8a4c-0c1f-4d20-9bdb-8c3bb5a4c8b8",
    "store_id": "STORE_BLR_002",
    "event_type": "ENTRY",
    "visitor_id": "VIS_c8a2f1",
    "camera_id": "CAM_ENTRY_01",
    "zone_id": "ENTRANCE",
    "timestamp": "2026-04-10T14:22:10Z",
    "is_staff": false,
    "confidence": 0.91,
    "dwell_ms": 0,
    "metadata": {"session_seq": 1}
  }'
```

### GET /stores/{store_id}/metrics
```bash
curl http://localhost:8000/stores/STORE_BLR_002/metrics
```

### GET /stores/{store_id}/funnel
```bash
curl http://localhost:8000/stores/STORE_BLR_002/funnel
```

### GET /stores/{store_id}/heatmap
```bash
curl http://localhost:8000/stores/STORE_BLR_002/heatmap
```

### GET /stores/{store_id}/anomalies
```bash
curl "http://localhost:8000/stores/STORE_BLR_002/anomalies?active_only=true&severity=CRITICAL"
```

### GET /stores/{store_id}/predict/queue
```bash
curl http://localhost:8000/stores/STORE_BLR_002/predict/queue
```

### GET /health
```bash
curl http://localhost:8000/health
```

### GET /metrics/prometheus
```bash
curl http://localhost:8000/metrics/prometheus
```

Legacy aliases (`/metrics`, `/funnel`, `/anomalies`, `/predict/queue`) default to `STORE_BLR_002`.

## Sample Event Payload

```json
{
  "event_id": "c2f6b2e0-1e6a-4ef5-9306-2b5b233a8c1d",
  "store_id": "STORE_BLR_002",
  "event_type": "ZONE_ENTER",
  "visitor_id": "VIS_c8a2f1",
  "camera_id": "CAM_FLOOR_02",
  "zone_id": "SKINCARE",
  "timestamp": "2026-04-10T10:28:14Z",
  "is_staff": false,
  "confidence": 0.88,
  "dwell_ms": 0,
  "metadata": {"session_seq": 3}
}
```

## Dashboard (Part E — Live)

The React dashboard at **http://localhost:3000** shows live visitor counts, funnel, heatmap, and anomaly feed via WebSocket (`/ws/live`).

## Seed Demo Data

```bash
docker compose exec api python -m database.seed
```

## Running Tests

```bash
cd STORE-IQ/storeiq
pip install -r requirements.txt
pytest tests/ -v --cov=. --cov-report=term-missing
```

All 51 tests passing ✅:
- `test_anomaly.py` (6 tests) — Anomaly detection logic
- `test_api.py` (7 tests) — API endpoints + idempotency
- `test_event_generator.py` (8 tests) — Event generation
- `test_event_processor.py` (3 tests) — Event persistence
- `test_events.py` (1 test) — Schema validation
- `test_funnel.py` (3 tests) — Funnel deduplication
- `test_integration.py` (1 test) — End-to-end flow
- `test_kafka.py` (3 tests) — Kafka producer/consumer
- `test_pos_loader.py` (2 tests) — POS ingestion
- `test_prediction.py` (5 tests) — Queue forecasting
- `test_staff_classifier.py` (2 tests) — Staff detection
- `test_tracker.py` (7 tests) — ByteTrack + Re-ID
- `test_zone_mapper.py` (3 tests) — Zone localization

---

## Architecture & Design

### Core Components

**Detection Pipeline** (`detector/` + `pipeline/`)
- **YOLOv11**: Real-time person detection (80-class model)
- **ByteTrack**: Multi-object tracking with IoU-based association
- **OSNet (TorchReID)**: Lightweight re-identification embeddings (~100MB) for cross-camera tracking
- **Zone Mapper**: Polygon-based spatial localization
- **Event Generator**: Structured event emission (ENTRY, EXIT, ZONE_*, BILLING_*, REENTRY)

**Backend API** (`api/`)
- **FastAPI** async web framework with Uvicorn/Gunicorn
- **PostgreSQL** with SQLAlchemy ORM for event persistence
- **Redis** for session state + feature store caching
- **Kafka** for decoupled event streaming
- **Middleware**: Structured JSON logging (trace_id, latency_ms), Prometheus metrics, rate limiting

**Database** (`database/`)
- **Event**: Globally unique events by event_id
- **SessionRecord**: Session-based deduplication (visitor journey)
- **MetricsHourly**: Time-series metrics snapshot
- **AnomalyRecord**: Detected anomalies with suggested actions
- **PosTransaction**: Conversion attribution via Brigade CSV
- **VisitorFeature**: Feature store for visitor analytics

**Analytics** (`analytics/`)
- **Funnel Engine**: 4-stage funnel (Entry → Zone Visit → Billing → Purchase)
- **Heatmap Engine**: Zone visit counts + dwell time
- **Prediction Engine**: Exponential smoothing for queue depth forecasting
- **Anomaly Engine**: 5 anomaly types (QUEUE_SPIKE, CONVERSION_DROP, DEAD_ZONE, CAMERA_OFFLINE, CROWD_ALERT)

**Frontend** (`dashboard/`)
- **React + Vite** with HMR
- **WebSocket** connection for real-time metrics
- **Recharts** visualizations
- **Tailwind CSS** styling

### Key Design Decisions

See [**DESIGN.md**](docs/DESIGN.md) for architecture rationale and [**CHOICES.md**](docs/CHOICES.md) for trade-off analysis.

**Highlights:**
- Event-first architecture with idempotency by `event_id`
- Session-based deduplication to avoid double-counting visitors
- Kafka decoupling for resilience + multi-consumer patterns
- Re-entry detection: same visitor exiting store, then re-entering counts as separate session
- Staff exclusion: uniform-based heuristic (HSV color) + manual flagging
- Group entry: 3+ people → 3 separate visitor IDs (not one group)

---

## Production Features

✅ **Error Handling** — Graceful 503 responses when database unavailable  
✅ **Idempotency** — Duplicate events rejected by event_id  
✅ **Logging** — Structured JSON with trace_id, latency_ms per request  
✅ **Rate Limiting** — 120 requests/minute (configurable)  
✅ **Monitoring** — Health endpoint with STALE_FEED warning (>10 min lag)  
✅ **Prometheus** — `/metrics/prometheus` endpoint for monitoring  
✅ **Scalability** — Designed for 40 stores + real-time event streaming  
✅ **Docker** — All services health-checked; zero manual setup  

---

## Environment Variables

See [`.env.example`](.env.example) for full configuration. Key settings:

```env
DATABASE_URL=postgresql+psycopg2://storeiq:storeiq@postgres:5432/storeiq
REDIS_URL=redis://redis:6379/0
KAFKA_BOOTSTRAP=kafka:9092
STORE_TIMEZONE=Asia/Kolkata
STALE_FEED_MINUTES=10
API_KEY=                              # Leave empty for local dev
CORS_ORIGINS=http://localhost:3000
USE_MOCK_DETECTION=true              # Set false for real YOLOv11
RATE_LIMIT_PER_MINUTE=120
```

---

## Troubleshooting

### Docker won't start services
```bash
docker compose config --quiet    # Check syntax
docker compose up --build -v     # Verbose logging
```

### API won't connect to database
```bash
# Wait for postgres to be ready (5-10 seconds)
docker compose logs postgres     # Check PostgreSQL logs
```

### Tests fail
```bash
pip install -r requirements.txt
pytest tests/ -v --tb=short
```

### WebSocket connection error on dashboard
```bash
# Check API is running
curl http://localhost:8000/health

# Verify CORS_ORIGINS matches dashboard host
echo $CORS_ORIGINS
```

### Large dataset/model files
- Videos (~650 MB): Not included in repo — place in `dataset/CCTV Footage/` locally
- Model weights (yolo11n.pt, osnet): Downloaded at runtime
- Dataset CSV/XLSX: Included in repo ✅

---

## Citation & Acknowledgments

Built for **UpGrad Placements Store Intelligence Challenge**.

**AI-Assisted Development:** Claude 3.5 Sonnet assisted with:
- Multi-stage ingestion architecture (Kafka decoupling)
- Re-ID embeddings selection
- Cache architecture optimization
- Test suite design + implementation

See [DESIGN.md](docs/DESIGN.md) AI-Assisted Decisions section for details.

---

## License

Purplle proprietary system. Challenge submission: 2026.

## Documentation

- [DESIGN.md](docs/DESIGN.md) — architecture, data flow, failure scenarios, **AI-Assisted Decisions**
- [CHOICES.md](docs/CHOICES.md) — detection model, event schema, and API architecture trade-offs
- [SCORING.md](docs/SCORING.md) — self-scoring rubric (harsh / realistic)

## Submission Checklist

- [x] `event_log.jsonl` — 2,426 events following `sample_events.jsonl` schema
- [x] `docker compose up` starts API, dashboard, Kafka, PostgreSQL, Redis
- [x] `GET /stores/STORE_BLR_002/metrics` returns valid JSON
- [x] `POST /events/ingest` accepts single and batch events (idempotent)
- [x] README explains detection pipeline against CCTV clips
- [x] `docs/DESIGN.md` includes AI-Assisted Decisions section
- [x] `docs/CHOICES.md` covers model selection, schema design, API decision
- [x] Prompt blocks at top of each test file
- [x] Live dashboard at http://localhost:3000
- [x] Challenge dataset (POS CSV + layout) bundled under `dataset/`
- [x] Staff exclusion, re-entry, and group entry handling
- [x] 51 unit/integration tests passing

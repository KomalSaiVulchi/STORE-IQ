<div align="center">

# 🛍️ Purplle StoreIQ

### AI-Powered Real-Time Store Intelligence System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-51%20passing-brightgreen.svg)](#-testing)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#)

**Store:** Brigade Road Bangalore (`STORE_BLR_002`) &nbsp;|&nbsp; **Cameras:** 5 &nbsp;|&nbsp; **Events Generated:** 2,426 &nbsp;|&nbsp; **Tests:** 51

</div>

---

## 📋 Submission Deliverables

All mandatory deliverables required by the challenge are present in this repository:

| # | Deliverable | File Path | Status |
|---|---|---|---|
| 1 | **Event Log (JSONL)** | `storeiq/event_log.jsonl` | ✅ 2,426 events |
| 2 | **README** | `README.md` / `storeiq/README.md` | ✅ This file |
| 3 | **DESIGN.md** (with AI-Assisted Decisions) | `storeiq/docs/DESIGN.md` | ✅ Complete |
| 4 | **CHOICES.md** (model, schema, API decisions) | `storeiq/docs/CHOICES.md` | ✅ Complete |

---

## 🧾 Event Log — `event_log.jsonl`

The primary deliverable. **2,426 chronological events** generated for Brigade Road Bangalore store on 2026-04-10, fully compliant with the provided `sample_events.jsonl` schema.

### Event Breakdown

| Event Type | Count | Description |
|---|---|---|
| `entry` | 333 | Visitor enters store at entry camera |
| `exit` | 333 | Visitor exits store at entry camera |
| `zone_entered` | 821 | Visitor enters a floor zone |
| `zone_exited` | 821 | Visitor exits a floor zone |
| `queue_completed` | 105 | Visitor successfully served at billing |
| `queue_abandoned` | 13 | Visitor abandons billing queue |
| **Total** | **2,426** | |

### Edge Cases Handled

| Edge Case | Detail |
|---|---|
| ✅ **Staff Exclusion** | 6 staff members with `is_staff: true`; filtered from all customer analytics |
| ✅ **Re-entry Detection** | ~5% of visitors re-enter correctly as a second `entry` event with same `id_token` |
| ✅ **Group Entry** | ~15% of visitors arrive in groups of 2–4; share `group_id`, each with unique `id_token` |
| ✅ **Queue Abandonment** | 13 events with `abandoned: true` and `queue_served_ts: null` |
| ✅ **Hidden Faces** | ~8% of entries have `is_face_hidden: true` |
| ✅ **Full Demographics** | `gender_pred`, `age_pred`, `age_bucket` on all entry/exit events |

### Regenerate the Event Log

```bash
cd storeiq
python3 generate_event_log.py
# ✅ Generated 2426 events → event_log.jsonl
```

---

## 🚀 How to Run Locally

Follow these step-by-step instructions to run the entire project on your local machine.

**Prerequisites:** 
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- Git installed.

**Step 1: Clone the repository**
Download the project to your local machine:
```bash
git clone https://github.com/KomalSaiVulchi/STORE-IQ.git
cd STORE-IQ/storeiq
```

**Step 2: Set up environment variables**
Create the `.env` file from the provided example:
```bash
cp .env.example .env
```
*(Optional: You can edit `.env` if you want to change default ports or passwords, but the defaults will work out-of-the-box).*

**Step 3: Start the services using Docker**
Build and start the entire stack (API, React Dashboard, PostgreSQL, Redis, Kafka, and Zookeeper):
```bash
docker compose up --build
```
*Note: The first time you run this, it may take a few minutes to download the base images and build the containers.*

**Step 4: Verify it's running**
Once you see logs indicating the services are running, open a new terminal tab and check the health endpoint:
```bash
curl http://localhost:8000/health
```

**Step 5: Access the Interfaces**
You can now access the system using your web browser:

| Service | URL |
|---|---|
| 🖥️ Live Dashboard | http://localhost:3000 |
| 📡 API | http://localhost:8000 |
| 📖 Swagger / Interactive Docs | http://localhost:8000/docs |
| ❤️ Health Check | http://localhost:8000/health |

---

## 🏗️ System Architecture

```
CCTV Cameras (5x)
      │
      ▼
┌─────────────────────────────────────┐
│          AI Detection Pipeline       │
│  YOLOv11  →  ByteTrack  →  OSNet   │  ← Person Detection, Tracking, ReID
│     (detector/)  (pipeline/)         │
└──────────────┬──────────────────────┘
               │ raw events
               ▼
┌──────────────────────────┐
│   Apache Kafka           │  ← Durable event streaming & buffering
│   Topic: raw_events      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│              FastAPI Backend                  │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐ │
│  │ Events   │  │ Analytics │  │ Anomaly   │ │
│  │ Ingest   │  │ Engine    │  │ Engine    │ │
│  └──────────┘  └───────────┘  └───────────┘ │
│         │             │              │        │
│         ▼             ▼              ▼        │
│  ┌─────────────┐  ┌────────┐  ┌──────────┐  │
│  │ PostgreSQL  │  │ Redis  │  │Prometheus│  │
│  │ (sessions) │  │(cache) │  │(metrics) │  │
│  └─────────────┘  └────────┘  └──────────┘  │
└──────────────────────┬───────────────────────┘
                       │ WebSocket (live feed)
                       ▼
            ┌────────────────────┐
            │   React Dashboard  │  ← Live charts, heatmaps, anomaly feed
            └────────────────────┘
```

---

## 📁 Project Structure

```
storeiq/
├── event_log.jsonl         ⭐ MANDATORY DELIVERABLE
├── generate_event_log.py   Script to regenerate event log
│
├── detector/               AI Detection Modules
│   ├── yolo_detector.py    YOLOv11 person detection
│   ├── bytetrack_wrapper.py ByteTrack multi-object tracking
│   ├── reid_engine.py      OSNet cross-camera re-identification
│   ├── staff_classifier.py HSV-based staff uniform detection
│   └── visitor_id.py       Unique visitor identity assignment
│
├── pipeline/               Video Processing Pipeline
│   ├── run_pipeline.py     Main pipeline entrypoint
│   ├── video_ingestion.py  RTSP/MP4 frame reader
│   ├── zone_mapper.py      Map coordinates → logical zones
│   ├── entry_detector.py   Entry/exit line crossing logic
│   ├── event_generator.py  Generate typed events
│   ├── session_engine.py   Visitor session lifecycle
│   ├── pos_loader.py       Load POS transaction data
│   ├── store_layout.json   Store physical layout config
│   └── zone_config.json    Zone polygon definitions
│
├── api/                    FastAPI REST Backend
│   ├── main.py             App entrypoint + lifespan
│   ├── models.py           Pydantic request/response models
│   ├── event_processor.py  Idempotent event ingestion logic
│   ├── websocket.py        WebSocket manager + broadcaster
│   ├── kafka_service.py    Kafka producer integration
│   ├── rate_limit.py       SlowAPI rate limiting
│   ├── middleware.py       Request logging + Prometheus metrics
│   └── routers/
│       ├── events.py       POST /events/ingest, /events/ingest/batch
│       ├── metrics.py      GET /stores/{id}/metrics
│       ├── funnel.py       GET /stores/{id}/funnel
│       ├── heatmap.py      GET /stores/{id}/heatmap
│       ├── anomalies.py    GET /stores/{id}/anomalies
│       ├── predict.py      GET /stores/{id}/predict/queue
│       └── health.py       GET /health
│
├── analytics/              Analytics Engines
│   ├── footfall_engine.py  Visitor count & dwell time
│   ├── funnel_engine.py    4-stage conversion funnel
│   ├── heatmap_engine.py   Zone-level heatmap generation
│   └── prediction_engine.py Queue depth forecasting (Prophet)
│
├── anomaly/
│   └── anomaly_engine.py   Z-score + rule-based anomaly detection
│
├── streaming/
│   ├── kafka_producer.py   Async Kafka event publisher
│   └── kafka_consumer.py   Kafka event consumer
│
├── database/
│   ├── models.py           SQLAlchemy ORM models
│   ├── seed.py             Seed DB with sample data
│   └── migrations/         Alembic migration scripts
│
├── feature_store/
│   └── feature_writer.py   Persist visitor embeddings to Redis
│
├── dashboard/              React Live Dashboard
│   └── src/components/
│       ├── LiveCounter.jsx
│       ├── FunnelChart.jsx
│       ├── ZoneHeatmap.jsx
│       ├── StoreTwin.jsx
│       ├── QueueForecast.jsx
│       ├── AnomalyFeed.jsx
│       └── PeakHoursChart.jsx
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.pipeline
│   ├── Dockerfile.dashboard
│   └── nginx.conf
│
├── docs/
│   ├── DESIGN.md           ⭐ Architecture + AI-Assisted Decisions
│   ├── CHOICES.md          ⭐ Model, schema & API trade-offs
│   └── SCORING.md          Self-scoring rubric
│
├── tests/                  51 Unit & Integration Tests
│   ├── test_api.py
│   ├── test_events.py
│   ├── test_event_processor.py
│   ├── test_event_generator.py
│   ├── test_funnel.py
│   ├── test_anomaly.py
│   ├── test_prediction.py
│   ├── test_staff_classifier.py
│   ├── test_tracker.py
│   ├── test_zone_mapper.py
│   ├── test_kafka.py
│   ├── test_pos_loader.py
│   └── test_integration.py
│
├── dataset/
│   ├── Brigade_Bangalore_10_April_26*.csv   POS transaction data
│   └── Brigade Road - Store layout*.xlsx    Physical store layout
│
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

---

## 📡 API Reference

All endpoints are available interactively at [http://localhost:8000/docs](http://localhost:8000/docs).

### Ingest Events

```bash
# Single event
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '{"event_type":"entry","store_id":"STORE_BLR_002","camera_id":"CAM_ENTRY_01","track_id":1,"is_staff":false,"confidence":0.97,"timestamp":"2026-04-10T10:00:00Z"}'

# Batch events
curl -X POST http://localhost:8000/events/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{"events": [...]}'
```

### Analytics Endpoints

```bash
# Store metrics (footfall, dwell time, conversion rate)
curl http://localhost:8000/stores/STORE_BLR_002/metrics

# 4-stage conversion funnel
curl http://localhost:8000/stores/STORE_BLR_002/funnel

# Zone heatmap (visit frequency per zone)
curl http://localhost:8000/stores/STORE_BLR_002/heatmap

# Anomalies (unusual traffic, camera issues)
curl http://localhost:8000/stores/STORE_BLR_002/anomalies

# Queue depth forecast (next 30 minutes)
curl http://localhost:8000/stores/STORE_BLR_002/predict/queue

# System health
curl http://localhost:8000/health
```

---

## 🧪 Testing

51 tests covering the full pipeline — event ingestion, analytics, Kafka, anomaly detection, tracking, and integration tests.

```bash
cd storeiq
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v --cov=.
```

| Test File | Coverage |
|---|---|
| `test_api.py` | Metrics, health, ingest, idempotency |
| `test_events.py` | Event schema validation |
| `test_event_processor.py` | Deduplication, persistence |
| `test_event_generator.py` | Simulated event correctness |
| `test_funnel.py` | Conversion funnel computation |
| `test_anomaly.py` | Z-score anomaly detection |
| `test_prediction.py` | Queue forecasting accuracy |
| `test_staff_classifier.py` | Uniform detection heuristic |
| `test_tracker.py` | ByteTrack wrapper |
| `test_zone_mapper.py` | Coordinate → zone mapping |
| `test_kafka.py` | Kafka producer/consumer mocks |
| `test_pos_loader.py` | POS CSV parsing |
| `test_integration.py` | End-to-end pipeline tests |

---

## 🎥 Running the Detection Pipeline

Process CCTV clips to generate live events (requires clips in `dataset/CCTV Footage/`).

```bash
# Inside the pipeline Docker container
docker exec -it storeiq-pipeline-1 bash
./pipeline/run.sh

# Or run directly with Python
python3 pipeline/run_pipeline.py \
  --store STORE_BLR_002 \
  --clip "dataset/CCTV Footage/entry_cam.mp4"
```

> **Note:** CCTV video files (~650 MB) are excluded from version control. The API works fully with seed data without them.

---

## 🗄️ Dataset & Reference Files

| File | Location | Purpose |
|---|---|---|
| POS Transactions | `dataset/Brigade_Bangalore_10_April_26*.csv` | Auto-loaded on API startup for purchase conversion rate |
| Store Layout | `dataset/Brigade Road - Store layout*.xlsx` | Physical dimensions used to define zone polygons |
| Zone Config | `pipeline/zone_config.json` | Polygon coordinates for each camera zone |
| Store Layout JSON | `pipeline/store_layout.json` | Logical store section definitions |
| Sample Events | `references/sample_eventsbe42122.jsonl` | HR-provided schema reference |
| Sample POS | `references/POS - sample transactions*.csv` | HR-provided transaction reference |

---

## 🔧 Environment Variables

```bash
# Copy the example and fill in your values
cp .env.example .env
```

Key variables (see `.env.example` for full list):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379` | Redis connection string |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address |
| `STORE_ID` | `STORE_BLR_002` | Default store identifier |

---

## 🤖 AI-Assisted Decisions

The following decisions were made with AI assistance (documented fully in [DESIGN.md](docs/DESIGN.md)):

1. **Multi-stage Ingestion via Kafka** — AI suggested decoupling the edge pipeline from the centralized API. Accepted.
2. **ReID Stack** — AI suggested a deep CNN-only stack. Rejected; OSNet chosen for edge latency constraints.
3. **Cache Architecture** — AI proposed a complex multi-tier cache. Rejected in favor of simpler Redis + PostgreSQL.

See [CHOICES.md](docs/CHOICES.md) for the full trade-off analysis on model selection, schema design, and API architecture.

---

## 📦 Submission Checklist

- [x] `event_log.jsonl` — 2,426 events matching `sample_events.jsonl` schema
- [x] `docs/DESIGN.md` — Architecture, data flow, and AI-Assisted Decisions section
- [x] `docs/CHOICES.md` — Detection model, schema design, and API architecture decisions
- [x] `README.md` — Complete setup and documentation (this file)
- [x] `docker compose up --build` — Starts full stack (API, Dashboard, Kafka, DB, Redis)
- [x] `POST /events/ingest` — Idempotent event ingestion (single + batch)
- [x] `GET /stores/STORE_BLR_002/metrics` — Returns visitor metrics
- [x] `GET /stores/STORE_BLR_002/funnel` — Returns conversion funnel
- [x] `GET /stores/STORE_BLR_002/heatmap` — Returns zone heatmap
- [x] `GET /stores/STORE_BLR_002/anomalies` — Returns detected anomalies
- [x] Staff exclusion, re-entry, group entry, queue abandonment all handled
- [x] Live React dashboard at http://localhost:3000
- [x] 51 unit/integration tests
- [x] CI/CD via GitHub Actions (`.github/workflows/ci.yml`)

---

<div align="center">

**Built for the UpGrad × Purplle Store Intelligence Challenge — 2026**

</div>

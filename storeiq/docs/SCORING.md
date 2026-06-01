# Self-Scoring Guide (Harsh / Realistic)

Use this to estimate your score **before** submission. Reviewers typically: clone repo → `docker compose up` → hit API/dashboard → skim `DESIGN.md` / `CHOICES.md` → optionally run `./pipeline/run.sh`.

**Target:** honest **70–85/100** with dataset in repo and pipeline run once.

---

## Rubric (100 points)

### 1. Video pipeline → events (25 pts)

| Criterion | Pts | How to verify | Your check |
|-----------|-----|---------------|------------|
| Runs on bundled `dataset/CCTV Footage/*.mp4` | 5 | `./pipeline/run.sh` completes, logs show events | ☐ |
| YOLO + tracking (not mock-only) | 5 | `USE_MOCK_DETECTION=false`, detections in logs | ☐ |
| Per-camera zones + entry line | 5 | Events have sensible `zone_id`, ENTRY on CAM 1 | ☐ |
| ReID / visitor IDs | 5 | Same person → same `VIS_*` across clips (spot-check) | ☐ |
| Staff excluded from footfall | 5 | `is_staff=true` on uniform-like detections | ☐ |

**Harsh deductions:** mock mode only (−10), zones never match video (−5), no pipeline run in README (−5).

---

### 2. API & event model (18 pts)

| Criterion | Pts | How to verify | Your check |
|-----------|-----|---------------|------------|
| `POST /events/ingest` single + batch + idempotent | 6 | `curl` twice same `event_id` → one row | ☐ |
| Sessions updated (ENTRY/EXIT/ZONE) | 6 | DB `sessions` rows after ingest | ☐ |
| Store-scoped routes | 3 | `/stores/STORE_BLR_002/metrics` | ☐ |
| Kafka path (optional bonus) | 3 | Events on topic + consumer persists | ☐ |

```bash
curl -s http://localhost:8000/stores/STORE_BLR_002/metrics | jq .
```

---

### 3. Analytics (18 pts)

| Criterion | Pts | How to verify | Your check |
|-----------|-----|---------------|------------|
| Funnel stages from sessions | 6 | `GET .../funnel` non-zero after pipeline | ☐ |
| POS-linked purchase stage | 6 | POS loaded; purchase count > 0 after exits | ☐ |
| Heatmap from events | 3 | `GET .../heatmap` reflects ZONE_ENTER | ☐ |
| Queue forecast | 3 | `GET .../predict/queue` returns JSON | ☐ |

**Harsh note:** POS has no `visitor_id` — time-window correlation is **heuristic** (expect partial credit only).

---

### 4. Anomaly detection (8 pts)

| Criterion | Pts | How to verify | Your check |
|-----------|-----|---------------|------------|
| Rule-based anomalies fire | 4 | `GET .../anomalies?active_only=true` | ☐ |
| Live evaluation after events | 4 | New anomalies after queue spike in data | ☐ |

---

### 5. Live dashboard — Part E (8 pts)

| Criterion | Pts | How to verify | Your check |
|-----------|-----|---------------|------------|
| WebSocket updates metrics | 4 | http://localhost:3000 changes after pipeline | ☐ |
| Funnel / heatmap / anomalies wired | 4 | No hardcoded-only charts after ingest | ☐ |

**Deduction:** seed data looks “live” but metrics are 0 (−3).

---

### 6. Documentation & design (13 pts)

| Criterion | Pts | How to verify | Your check |
|-----------|-----|---------------|------------|
| README quick start works | 4 | 5-command flow from README | ☐ |
| `docs/DESIGN.md` + AI decisions | 5 | Section present | ☐ |
| `docs/CHOICES.md` trade-offs | 4 | Model/schema/API covered | ☐ |

---

### 7. Tests, CI, ops (10 pts)

| Criterion | Pts | How to verify | Your check |
|-----------|-----|---------------|------------|
| `pytest tests/` passes | 4 | CI green on GitHub | ☐ |
| `docker compose up --build` | 4 | All services healthy | ☐ |
| Dataset in repo (`dataset/`) | 2 | Reviewer needs no external folder | ☐ |

---

## Quick score formula

1. Go through each ☐ after a full run.
2. Sum points for checked items.
3. Apply **honesty tax**:
   - Pipeline never run on your machine: **−15**
   - Dashboard only seed data: **−5**
   - No POS loaded: **−5**

---

## Recommended submission demo (15 min)

```bash
cd storeiq
cp .env.example .env
docker compose up --build -d
# Wait for API healthy, then:
./pipeline/run.sh   # or: docker compose run --rm pipeline python -m pipeline.run_pipeline
curl -s http://localhost:8000/stores/STORE_BLR_002/metrics | jq .
curl -s http://localhost:8000/stores/STORE_BLR_002/funnel | jq .
open http://localhost:3000
```

Paste **metrics + funnel JSON** (or screenshot) into README under “Sample output” for **+3–5** reviewer confidence.

---

## Expected bands

| Preparation | Realistic score |
|-------------|-----------------|
| Repo only, no dataset, never ran pipeline | 62–72 |
| Dataset in repo, compose works, no pipeline run | 68–76 |
| Dataset + pipeline run + README sample output | **75–85** |
| Above + calibrated zones + real YOLO on all 5 cams | 82–88 |

90+ usually needs **demonstrably accurate** multi-camera ReID and **validated** conversion vs POS — hard in a weekend build.

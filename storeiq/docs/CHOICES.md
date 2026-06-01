# Trade-off Choices

This document outlines the major architectural and design trade-offs made during the development of Purplle StoreIQ.

## Decision 1: Detection Model (YOLOv11 vs. Alternatives)
- **Options Considered**: YOLOv8, YOLOv11, RT-DETR, Faster R-CNN.
- **AI Suggestion**: Claude recommended exploring RT-DETR for its transformer-based accuracy improvements.
- **Chosen Option**: YOLOv11.
- **Reasoning**: While RT-DETR offers excellent accuracy, it struggles to meet the strict <500ms end-to-end latency constraint on edge hardware without significant optimization (TensorRT). YOLOv11 provides the best out-of-the-box balance of speed and accuracy, and its native integration with the Ultralytics package simplified deployment. Faster R-CNN was rejected immediately due to its slow inference speed.

## Decision 2: Tracking and Re-Identification Strategy
- **Options Considered**: DeepSORT, ByteTrack + OSNet, StrongSORT.
- **AI Suggestion**: ChatGPT suggested DeepSORT due to its popularity and integrated appearance features.
- **Chosen Option**: ByteTrack + OSNet (TorchReID).
- **Reasoning**: DeepSORT tightly couples tracking and ReID, which can become a bottleneck when scaling to multiple high-resolution cameras. ByteTrack relies solely on bounding box associations (IoU) for tracking, making it exceptionally fast and resilient to occlusions. We decoupled ReID by using OSNet only when tracks transition between cameras or re-enter, significantly reducing the compute load. OSNet was chosen for its lightweight architecture and strong performance on person re-identification benchmarks (e.g., Market-1501).

## Decision 3: Event Schema Design
- **Options Considered**: Flat generic schema vs. Highly structured typed schema.
- **AI Suggestion**: Claude recommended a session-first design where events are aggregated before ingestion.
- **Chosen Option**: Highly structured typed schema with raw event ingestion.
- **Reasoning**: A session-first design at the edge complicates handling network partitions and delays. By emitting granular, structured raw events (`event_id`, `store_id`, `is_staff`, `confidence`, `dwell_ms`, `metadata`), we enable idempotent ingestion at the API layer. The `event_id` UUID prevents race conditions, and the JSONB `metadata` column in PostgreSQL allows future extensibility without costly schema migrations. Sessions are reconstructed asynchronously in the backend, ensuring data integrity.

## Decision 4: Backend Architecture (FastAPI + PostgreSQL + Kafka)
- **Options Considered**: Node.js + MongoDB, FastAPI + PostgreSQL + Kafka, Go + ClickHouse.
- **AI Suggestion**: ChatGPT proposed Node.js + MongoDB for rapid prototyping and flexible JSON handling.
- **Chosen Option**: FastAPI + PostgreSQL + Kafka.
- **Reasoning**: FastAPI offers async performance, robust validation via Pydantic (crucial for enforcing the event schema), and auto-generated Swagger documentation. PostgreSQL provides strong ACID guarantees and supports flexible JSONB querying, which is vital for our metadata. Kafka was introduced to provide durable event streaming and decoupled consumer scaling, allowing the pipeline to buffer events during API or database outages, thereby satisfying the high-availability requirement.

## Decision 5: Staff Detection Strategy
- **Options Considered**: VLM-based uniform classification, dedicated staff detector model, HSV color heuristic on upper-body crop.
- **AI Suggestion**: Claude suggested using GPT-4V to classify staff from uniform appearance in sample frames.
- **Chosen Option**: HSV color heuristic (`detector/staff_classifier.py`) applied per-detection bounding box.
- **Reasoning**: VLM inference adds latency and cost per frame, violating the <500ms constraint. A lightweight heuristic targeting dark Purplle-branded uniforms achieves sufficient accuracy for staff exclusion in metrics, with `is_staff=true` propagated through the event schema and filtered at the API layer. We documented the VLM approach as a future upgrade path if uniform styles vary across stores.

"""Run the StoreIQ video pipeline."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.event_processor import persist_event
from detector.bytetrack_wrapper import ByteTrackWrapper
from detector.reid_engine import ReIDEngine
from detector.yolo_detector import YoloDetector
from pipeline.entry_detector import EntryLineDetector
from pipeline.event_generator import EventGenerator
from pipeline.video_ingestion import event_to_payload, stream_frames
from pipeline.zone_mapper import ZoneMapper
from streaming.kafka_producer import KafkaProducerClient
from api.middleware import configure_logger
from api.config import get_settings


def _persist_event_sync(session_local, payload: dict) -> None:
    """Persist event to PostgreSQL in a worker thread."""
    with session_local() as db:
        persist_event(db, payload)


async def process_camera(
    camera_id: str,
    source: str,
    zone_path: str,
    settings,
    redis_client,
    session_local,
    reid: ReIDEngine,
    producer: KafkaProducerClient,
    logger,
    executor: ThreadPoolExecutor,
) -> None:
    """Process a single camera stream."""
    detector = YoloDetector()
    tracker = ByteTrackWrapper()
    is_entry_camera = "ENTRY" in camera_id.upper()
    zone_mapper = ZoneMapper.for_camera(zone_path, camera_id)
    entry_detector = None
    if is_entry_camera and zone_mapper.entry_line_y is not None:
        entry_detector = EntryLineDetector(line_y=zone_mapper.entry_line_y)
    store_id = os.getenv("STORE_ID", "STORE_BLR_002")
    event_generator = EventGenerator(store_id=store_id, is_entry_camera=is_entry_camera)

    active_tracks = {}
    track_visitors = {}
    frame_count = 0
    frame_skip = settings.frame_skip
    frame_visitor_ids: set[str] = set()

    logger.info(
        {
            "camera_id": camera_id,
            "source": source,
            "message": "Starting camera pipeline",
            "frame_skip": frame_skip,
        }
    )

    loop = asyncio.get_event_loop()

    for frame, timestamp in stream_frames(source):
        frame_count += 1
        frame_visitor_ids.clear()

        if frame_count % frame_skip != 0:
            continue

        detections = detector.detect(frame)
        tracks = tracker.update(detections)
        now = timestamp

        for track in tracks:
            embedding = reid.extract_embedding(frame, track.bbox, track_id=track.track_id)
            # Group handling: never assign the same visitor_id to two active tracks in one frame
            result = reid.resolve(
                embedding,
                camera_id=camera_id,
                seen_at=now,
                exclude_visitor_ids=frame_visitor_ids,
            )
            frame_visitor_ids.add(result.visitor_id)

            cx = int((track.bbox[0] + track.bbox[2]) / 2)
            cy = int((track.bbox[1] + track.bbox[3]) / 2)
            zone_id = zone_mapper.resolve((cx, cy))
            entry_cross = entry_detector.update(track.track_id, cy) if entry_detector else None
            events = event_generator.update(
                track.track_id,
                result.visitor_id,
                camera_id,
                zone_id,
                timestamp=now,
                confidence=track.confidence,
                is_staff=track.is_staff,
                entry_cross=entry_cross,
            )
            track_visitors[track.track_id] = result.visitor_id

            for event in events:
                payload = event_to_payload(event)
                try:
                    await producer.send(settings.kafka_raw_topic, payload)
                except Exception as exc:
                    logger.warning({"message": "Kafka send failed", "error": str(exc)})

                await loop.run_in_executor(
                    executor,
                    partial(_persist_event_sync, session_local, payload),
                )

                logger.info(
                    {
                        "trace_id": str(uuid.uuid4()),
                        "event_type": event.event_type,
                        "visitor_id": event.visitor_id,
                        "camera_id": event.camera_id,
                        "zone_id": event.zone_id,
                        "is_staff": event.is_staff,
                        "timestamp": payload["timestamp"],
                    }
                )

            active_tracks[track.track_id] = now

        expired = [track_id for track_id, last_seen in active_tracks.items() if now - last_seen > 2.0]
        for track_id in expired:
            visitor_id = track_visitors.get(track_id, "unknown")
            if entry_detector:
                entry_detector.clear(track_id)
            events = event_generator.close_track(track_id, visitor_id, camera_id, timestamp=now)
            reid.clear_track_cache(track_id)
            for event in events:
                payload = event_to_payload(event)
                try:
                    await producer.send(settings.kafka_raw_topic, payload)
                except Exception as exc:
                    logger.warning({"message": "Kafka send failed on track close", "error": str(exc)})
                await loop.run_in_executor(
                    executor,
                    partial(_persist_event_sync, session_local, payload),
                )
            active_tracks.pop(track_id, None)
            track_visitors.pop(track_id, None)

        redis_client.set(f"pipeline:{camera_id}:last_frame_ts", now)
        redis_client.set(f"pipeline:{camera_id}:frame_count", frame_count)

    logger.info({"camera_id": camera_id, "message": "Camera pipeline finished", "total_frames": frame_count})


async def run_pipeline() -> None:
    """Main pipeline loop — supports multiple cameras concurrently."""
    settings = get_settings()
    logger = configure_logger("storeiq-pipeline")

    camera_sources_raw = os.getenv("CAMERA_SOURCES", "")
    camera_sources = {}
    if camera_sources_raw:
        for pair in camera_sources_raw.split(","):
            if "=" in pair:
                cam_id, source = pair.strip().split("=", 1)
                camera_sources[cam_id.strip()] = source.strip()

    if not camera_sources:
        source = os.getenv("VIDEO_SOURCE", os.getenv("SAMPLE_VIDEO_PATH", "./pipeline/sample_video.mp4"))
        camera_sources["CAM_ENTRY_01"] = source

    zone_path = os.getenv("ZONE_CONFIG_PATH", "./pipeline/zone_config.json")
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    db_engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
    )
    session_local = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)

    reid = ReIDEngine(settings.redis_url)
    producer = KafkaProducerClient(settings.kafka_bootstrap)
    await producer.start()

    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="db-pool")

    logger.info(
        {
            "message": "Pipeline starting",
            "cameras": list(camera_sources.keys()),
            "frame_skip": settings.frame_skip,
        }
    )

    tasks = [
        process_camera(
            camera_id=cam_id,
            source=source,
            zone_path=zone_path,
            settings=settings,
            redis_client=redis_client,
            session_local=session_local,
            reid=reid,
            producer=producer,
            logger=logger,
            executor=executor,
        )
        for cam_id, source in camera_sources.items()
    ]

    try:
        await asyncio.gather(*tasks)
    finally:
        Path("/tmp/pipeline_healthy").write_text("ok")
        await producer.stop()
        executor.shutdown(wait=False)
        logger.info({"message": "Pipeline shutdown complete"})


def main() -> None:
    """Run the async pipeline entrypoint."""
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()

"""Seed the database with realistic demo data."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.config import get_settings
from database.models import AnomalyRecord, MetricsHourly, SessionRecord


def seed() -> None:
    """Populate the database with demo metrics, sessions, and anomalies."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    rng = random.Random(42)

    now = datetime.now(timezone.utc)
    hours = [now - timedelta(hours=hour) for hour in range(7 * 24)]
    hours.reverse()

    with session_local() as db:
        db.query(MetricsHourly).delete()
        db.query(SessionRecord).delete()
        db.query(AnomalyRecord).delete()
        db.commit()

        for bucket in hours:
            hour = bucket.hour
            peak = 1.0
            if 11 <= hour <= 14 or 17 <= hour <= 20:
                peak = 1.6
            visitors = int(rng.randint(8, 25) * peak)
            avg_dwell = rng.uniform(240, 600)
            conversion = rng.uniform(8, 16)
            zone_scores = {
                "SKINCARE": int(rng.uniform(70, 92)),
                "MAKEUP": int(rng.uniform(55, 78)),
                "HAIRCARE": int(rng.uniform(30, 55)),
                "BILLING": int(rng.uniform(35, 60)),
                "ENTRANCE": int(rng.uniform(40, 65)),
            }
            queue_depth = rng.uniform(1, 8)
            db.add(
                MetricsHourly(
                    hour_bucket=bucket,
                    unique_visitors=visitors,
                    avg_dwell_sec=avg_dwell,
                    conversion_rate=conversion,
                    zone_scores=zone_scores,
                    queue_depth_avg=queue_depth,
                )
            )

        for _ in range(500):
            entry = now - timedelta(days=rng.randint(0, 6), hours=rng.randint(0, 23))
            dwell = rng.randint(120, 1800)
            exit_time = entry + timedelta(seconds=dwell)
            zones = rng.sample(["SKINCARE", "MAKEUP", "HAIRCARE", "BILLING"], rng.randint(1, 3))
            billing = "BILLING" in zones
            purchase = billing and rng.random() > 0.6
            db.add(
                SessionRecord(
                    session_id=str(uuid.uuid4()),
                    visitor_id=str(uuid.uuid4()),
                    entry_time=entry,
                    exit_time=exit_time,
                    zones_visited=zones,
                    billing_visited=billing,
                    purchase=purchase,
                    dwell_seconds=dwell,
                    reentry=rng.random() > 0.85,
                    camera_path=["cam_01", "cam_02"],
                )
            )

        for _ in range(20):
            severity = rng.choice(["WARN", "CRITICAL"])
            anomaly_type = rng.choice(["QUEUE_SPIKE", "DEAD_ZONE", "CONVERSION_DROP", "CAMERA_OFFLINE", "CROWD_ALERT"])
            db.add(
                AnomalyRecord(
                    anomaly_id=str(uuid.uuid4()),
                    type=anomaly_type,
                    severity=severity,
                    confidence=round(rng.uniform(0.6, 0.98), 2),
                    reason="Synthetic seed anomaly",
                    zone_id=rng.choice(["SKINCARE", "MAKEUP", "HAIRCARE", "BILLING", None]),
                    resolved=rng.random() > 0.7,
                    created_at=now - timedelta(hours=rng.randint(0, 72)),
                )
            )

        db.commit()


def seed_metrics_only() -> None:
    """Seed only hourly metrics baselines — no fake sessions or anomalies."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    rng = random.Random(42)

    now = datetime.now(timezone.utc)
    hours = [now - timedelta(hours=hour) for hour in range(7 * 24)]
    hours.reverse()

    with session_local() as db:
        if db.query(MetricsHourly).count() > 0:
            return
        for bucket in hours:
            hour = bucket.hour
            peak = 1.0
            if 11 <= hour <= 14 or 17 <= hour <= 20:
                peak = 1.6
            visitors = int(rng.randint(8, 25) * peak)
            avg_dwell = rng.uniform(240, 600)
            conversion = rng.uniform(8, 16)
            zone_scores = {
                "SKINCARE": int(rng.uniform(70, 92)),
                "MAKEUP": int(rng.uniform(55, 78)),
                "HAIRCARE": int(rng.uniform(30, 55)),
                "BILLING": int(rng.uniform(35, 60)),
                "ENTRANCE": int(rng.uniform(40, 65)),
            }
            queue_depth = rng.uniform(1, 8)
            db.add(
                MetricsHourly(
                    hour_bucket=bucket,
                    unique_visitors=visitors,
                    avg_dwell_sec=avg_dwell,
                    conversion_rate=conversion,
                    zone_scores=zone_scores,
                    queue_depth_avg=queue_depth,
                )
            )
        db.commit()


if __name__ == "__main__":
    seed()

"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for StoreIQ models."""


class Event(Base):
    """Events table."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    store_id = Column(String(30), nullable=False, index=True, default="STORE_BLR_002")
    event_type = Column(String(50), nullable=False)
    visitor_id = Column(String(64), nullable=False, index=True)
    track_id = Column(Integer, nullable=True)
    camera_id = Column(String(20), nullable=True)
    zone_id = Column(String(30), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    is_staff = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)
    dwell_ms = Column(Integer, nullable=True, default=0)
    metadata_json = Column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("ix_events_store_ts", "store_id", "timestamp"),
        Index("ix_events_visitor_ts", "visitor_id", "timestamp"),
        Index("ix_events_camera_ts", "camera_id", "timestamp"),
        Index("ix_events_type_ts", "event_type", "timestamp"),
        Index("ix_events_store_type", "store_id", "event_type"),
    )


class SessionRecord(Base):
    """Sessions table."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    store_id = Column(String(30), nullable=False, index=True, default="STORE_BLR_002")
    visitor_id = Column(String(64), nullable=False, index=True)
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    exit_time = Column(DateTime(timezone=True), nullable=True, index=True)
    zones_visited = Column(JSONB, nullable=True)
    billing_visited = Column(Boolean, default=False, index=True)
    purchase = Column(Boolean, default=False, index=True)
    dwell_seconds = Column(Integer, nullable=True)
    reentry = Column(Boolean, default=False)
    camera_path = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_sessions_store_entry", "store_id", "entry_time"),
        Index("ix_sessions_visitor_entry", "visitor_id", "entry_time"),
        Index("ix_sessions_billing_purchase", "billing_visited", "purchase"),
    )


class MetricsHourly(Base):
    """Metrics hourly table."""

    __tablename__ = "metrics_hourly"

    id = Column(Integer, primary_key=True)
    hour_bucket = Column(DateTime(timezone=True), nullable=False, index=True)
    unique_visitors = Column(Integer, nullable=True)
    avg_dwell_sec = Column(Float, nullable=True)
    conversion_rate = Column(Float, nullable=True)
    zone_scores = Column(JSONB, nullable=True)
    queue_depth_avg = Column(Float, nullable=True)


class AnomalyRecord(Base):
    """Anomalies table."""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True)
    anomaly_id = Column(String, unique=True, nullable=False, index=True)
    store_id = Column(String(30), nullable=False, index=True, default="STORE_BLR_002")
    type = Column(String(50), nullable=False, index=True)
    severity = Column(String(10), nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    zone_id = Column(String(30), nullable=True, index=True)
    resolved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_anomalies_store_severity", "store_id", "severity", "resolved"),
        Index("ix_anomalies_severity_resolved", "severity", "resolved"),
        Index("ix_anomalies_type_created", "type", "created_at"),
    )


class PosTransaction(Base):
    """POS transactions table for conversion rate correlation."""

    __tablename__ = "pos_transactions"

    id = Column(Integer, primary_key=True)
    store_id = Column(String(30), nullable=False, index=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    basket_value_inr = Column(Float, nullable=True)
    invoice_number = Column(String(64), nullable=True)
    customer_name = Column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_pos_store_ts", "store_id", "timestamp"),
    )


class VisitorFeature(Base):
    """Visitor feature store table."""

    __tablename__ = "visitor_features"

    visitor_id = Column(String(64), primary_key=True)
    avg_dwell_sec = Column(Float, nullable=True)
    visit_count = Column(Integer, nullable=True)
    zone_affinity = Column(JSONB, nullable=True)
    billing_rate = Column(Float, nullable=True)
    conversion_rate = Column(Float, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True, index=True)

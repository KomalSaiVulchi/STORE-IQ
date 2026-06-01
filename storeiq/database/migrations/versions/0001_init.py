"""Initial schema migration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create core tables."""
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("visitor_id", sa.String(length=64), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("camera_id", sa.String(length=20), nullable=True),
        sa.Column("zone_id", sa.String(length=30), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False, unique=True),
        sa.Column("visitor_id", sa.String(length=64), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("zones_visited", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("billing_visited", sa.Boolean(), default=False),
        sa.Column("purchase", sa.Boolean(), default=False),
        sa.Column("dwell_seconds", sa.Integer(), nullable=True),
        sa.Column("reentry", sa.Boolean(), default=False),
        sa.Column("camera_path", postgresql.ARRAY(sa.Text()), nullable=True),
    )
    op.create_table(
        "metrics_hourly",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hour_bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unique_visitors", sa.Integer(), nullable=True),
        sa.Column("avg_dwell_sec", sa.Float(), nullable=True),
        sa.Column("conversion_rate", sa.Float(), nullable=True),
        sa.Column("zone_scores", postgresql.JSONB(), nullable=True),
        sa.Column("queue_depth_avg", sa.Float(), nullable=True),
    )
    op.create_table(
        "anomalies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anomaly_id", sa.String(), nullable=False, unique=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("zone_id", sa.String(length=30), nullable=True),
        sa.Column("resolved", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "visitor_features",
        sa.Column("visitor_id", sa.String(length=64), primary_key=True),
        sa.Column("avg_dwell_sec", sa.Float(), nullable=True),
        sa.Column("visit_count", sa.Integer(), nullable=True),
        sa.Column("zone_affinity", postgresql.JSONB(), nullable=True),
        sa.Column("billing_rate", sa.Float(), nullable=True),
        sa.Column("conversion_rate", sa.Float(), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Drop core tables."""
    op.drop_table("visitor_features")
    op.drop_table("anomalies")
    op.drop_table("metrics_hourly")
    op.drop_table("sessions")
    op.drop_table("events")

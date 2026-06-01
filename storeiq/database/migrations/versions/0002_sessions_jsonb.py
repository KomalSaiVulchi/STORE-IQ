"""Migrate session list columns from ARRAY to JSONB."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_sessions_jsonb"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE sessions ALTER COLUMN zones_visited TYPE jsonb "
        "USING to_jsonb(zones_visited)"
    )
    op.execute(
        "ALTER TABLE sessions ALTER COLUMN camera_path TYPE jsonb "
        "USING to_jsonb(camera_path)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE sessions ALTER COLUMN zones_visited TYPE text[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(zones_visited))"
    )
    op.execute(
        "ALTER TABLE sessions ALTER COLUMN camera_path TYPE text[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(camera_path))"
    )

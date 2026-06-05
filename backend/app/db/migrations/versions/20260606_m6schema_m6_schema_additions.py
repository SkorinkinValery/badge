"""m6_schema_additions

Revision ID: m6schema
Revises: 4b47e88b70e8
Create Date: 2026-06-06 00:00:00.000000+00:00

Adds:
  - script.active_version_id (UUID, nullable) — active script version pointer
  - recording.duration_seconds (Float, nullable) — call duration for daily summary

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "m6schema"
down_revision: str | None = "4b47e88b70e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("script", sa.Column("active_version_id", sa.Uuid(), nullable=True))
    op.add_column("recording", sa.Column("duration_seconds", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("recording", "duration_seconds")
    op.drop_column("script", "active_version_id")

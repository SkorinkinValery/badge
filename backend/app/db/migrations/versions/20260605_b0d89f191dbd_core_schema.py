"""core_schema

Revision ID: b0d89f191dbd
Revises: 0001baseline
Create Date: 2026-06-05 17:50:31.015809+00:00

Создаёт core-таблицы (user, manager, script, script_ver, recording,
transcript, analysis) в том виде, в каком они существовали на момент этой
ревизии. Колонки, добавленные позднее (analysis.auto_score/corrected_by,
script.active_version_id, recording.duration_seconds, user.is_active),
тут отсутствуют — их добавляют последующие миграции 4b47e88b70e8 /
m6schema / cc27a3cf97ac, поэтому `alembic upgrade head` отрабатывает
на пустой базе.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b0d89f191dbd'
down_revision: str | None = '0001baseline'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("login", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login"),
    )

    op.create_table(
        "manager",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.String(length=255), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("default_script_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "script",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "script_ver",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("script_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("kpi_binding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["script_id"], ["script.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "recording",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manager_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("consent_flag", sa.Boolean(), nullable=False),
        sa.Column("audio_path", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage_error", sa.Text(), nullable=True),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["manager_id"], ["manager.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recording_manager_id", "recording", ["manager_id"])
    op.create_index("ix_recording_status", "recording", ["status"])

    op.create_table(
        "transcript",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("segments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("detected_language", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["recording_id"], ["recording.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_recording_id", "transcript", ["recording_id"])

    op.create_table(
        "analysis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("kpi_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(length=4), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("script_version_id", sa.Uuid(), nullable=True),
        sa.Column("weights_version", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["recording_id"], ["recording.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_recording_id", "analysis", ["recording_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_recording_id", table_name="analysis")
    op.drop_table("analysis")
    op.drop_index("ix_transcript_recording_id", table_name="transcript")
    op.drop_table("transcript")
    op.drop_index("ix_recording_status", table_name="recording")
    op.drop_index("ix_recording_manager_id", table_name="recording")
    op.drop_table("recording")
    op.drop_table("script_ver")
    op.drop_table("script")
    op.drop_table("manager")
    op.drop_table("user")

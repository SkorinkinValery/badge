"""add_auto_score_corrected_by_to_analysis

Revision ID: 4b47e88b70e8
Revises: b0d89f191dbd
Create Date: 2026-06-05 19:29:59.705118+00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '4b47e88b70e8'
down_revision: str | None = 'b0d89f191dbd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('analysis', sa.Column('auto_score', sa.Float(), nullable=True))
    op.add_column('analysis', sa.Column('corrected_by', sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column('analysis', 'corrected_by')
    op.drop_column('analysis', 'auto_score')

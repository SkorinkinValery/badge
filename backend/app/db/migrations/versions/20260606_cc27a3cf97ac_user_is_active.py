"""user_is_active

Revision ID: cc27a3cf97ac
Revises: m6schema
Create Date: 2026-06-06 22:19:09.714950+00:00

Adds:
  - user.is_active (Boolean, NOT NULL, default True) — soft-disable flag for user accounts.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc27a3cf97ac"
down_revision: str | None = "m6schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "is_active")

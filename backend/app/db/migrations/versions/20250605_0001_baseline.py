"""baseline

Revision ID: 0001baseline
Revises:
Create Date: 2025-06-05 00:00:00.000000 UTC

"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Baseline migration — no schema changes yet.
    # Domain models (manager, recording, transcript, analysis, user, script)
    # will be added in M1 migrations.
    pass


def downgrade() -> None:
    pass

"""purge_retention.py — cron entry-point for retention-based deletion (C2).

Finds recordings whose retention_until has passed, deletes their audio
objects from MinIO and removes the DB rows (transcript/analysis cascade).

Usage:
    python scripts/purge_retention.py [--dry-run]

Exit codes:
    0 — success (including dry-run)
    1 — unhandled error
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure backend/ is on the path when run from project root or scripts/
_BACKEND = Path(__file__).parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Purge recordings whose retention period has expired."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List candidates only — nothing is deleted.",
    )
    return parser.parse_args()


async def _run(dry_run: bool) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config.settings import Settings
    from app.services.retention import purge_expired_recordings
    from app.services.storage import ObjectStorage

    settings = Settings()

    engine = create_async_engine(settings.database_url, echo=False)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    storage = ObjectStorage(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        bucket=settings.minio_bucket,
    )

    async with factory() as session:
        async with session.begin():
            result = await purge_expired_recordings(session, storage, dry_run=dry_run)

    await engine.dispose()

    if dry_run:
        print(f"[dry-run] {result.count} recording(s) would be purged:")
    else:
        print(f"Purged {result.count} recording(s):")

    for rid in result.purged_ids:
        print(f"  {rid}")


def main() -> None:
    args = _parse_args()
    try:
        asyncio.run(_run(dry_run=args.dry_run))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Integration tests for ObjectStorage (MinIO backend) — M2-T1.

Requires a running MinIO. Set MINIO_ENDPOINT env or use docker compose.
"""

from __future__ import annotations

import io
import os
import uuid

import pytest

pytestmark = pytest.mark.integration

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
TEST_BUCKET = "test-audio"


@pytest.fixture(scope="module")
def storage():  # type: ignore[no-untyped-def]
    from app.services.storage import ObjectStorage

    s = ObjectStorage(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        bucket=TEST_BUCKET,
    )
    s.ensure_bucket()
    yield s


class TestObjectStorage:
    def test_put_and_get_roundtrip(self, storage) -> None:  # type: ignore[no-untyped-def]
        from app.services.storage import ObjectStorage

        key = f"recordings/{uuid.uuid4()}/original.wav"
        data = b"\x00\x01\x02\x03\xff" * 100
        returned_key = storage.put_object(key, io.BytesIO(data), len(data), "audio/wav")
        assert returned_key == key

        result = storage.get_object(key)
        assert result.read() == data

    def test_put_generates_deterministic_key(self, storage) -> None:  # type: ignore[no-untyped-def]
        from app.services.storage import ObjectStorage as OS

        rid = uuid.uuid4()
        key = OS.make_key(rid, "original", ".mp3")
        assert key == f"recordings/{rid}/original.mp3"

    def test_presigned_url_is_string(self, storage) -> None:  # type: ignore[no-untyped-def]
        key = f"recordings/{uuid.uuid4()}/original.wav"
        data = b"wave"
        storage.put_object(key, io.BytesIO(data), len(data), "audio/wav")
        url = storage.presigned_url(key)
        assert isinstance(url, str)
        assert key.split("/")[-1] in url or "recordings" in url

    def test_get_missing_key_raises(self, storage) -> None:  # type: ignore[no-untyped-def]
        from app.services.storage import StorageKeyNotFoundError

        with pytest.raises(StorageKeyNotFoundError):
            storage.get_object(f"recordings/{uuid.uuid4()}/missing.wav")

    def test_ensure_bucket_idempotent(self, storage) -> None:  # type: ignore[no-untyped-def]
        storage.ensure_bucket()  # second call must not raise

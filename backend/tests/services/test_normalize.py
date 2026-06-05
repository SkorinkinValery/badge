"""Integration tests for ffmpeg audio normalization — M2-T3.

Requires ffmpeg on PATH and a running MinIO.
"""

from __future__ import annotations

import io
import os
import struct
import uuid

import pytest

pytestmark = pytest.mark.integration

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ROOT_USER = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
TEST_BUCKET = "test-normalize"


def _make_wav(duration_s: float = 0.5, sample_rate: int = 44100) -> bytes:
    num_samples = int(duration_s * sample_rate)
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size


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


class TestNormalizeAudio:
    def test_wav_normalized_to_target_format(self, storage) -> None:  # type: ignore[no-untyped-def]
        from app.services.normalize import normalize_audio

        rid = uuid.uuid4()
        wav_data = _make_wav(duration_s=0.5, sample_rate=44100)
        orig_key = storage.put_object(
            f"recordings/{rid}/original.wav",
            io.BytesIO(wav_data),
            len(wav_data),
            "audio/wav",
        )

        norm_key = normalize_audio(rid, orig_key, storage)

        assert norm_key.endswith(".wav") or norm_key.endswith(".pcm")
        result = storage.get_object(norm_key)
        assert len(result.read()) > 0

    def test_normalized_file_is_16khz_mono(self, storage) -> None:  # type: ignore[no-untyped-def]
        import wave

        from app.services.normalize import normalize_audio

        rid = uuid.uuid4()
        wav_data = _make_wav(duration_s=1.0, sample_rate=48000)
        orig_key = storage.put_object(
            f"recordings/{rid}/original.wav",
            io.BytesIO(wav_data),
            len(wav_data),
            "audio/wav",
        )

        norm_key = normalize_audio(rid, orig_key, storage)
        norm_bytes = storage.get_object(norm_key).read()

        with wave.open(io.BytesIO(norm_bytes)) as wf:
            assert wf.getframerate() == 16000
            assert wf.getnchannels() == 1

    def test_broken_file_raises(self, storage) -> None:  # type: ignore[no-untyped-def]
        from app.services.normalize import NormalizationError, normalize_audio

        rid = uuid.uuid4()
        garbage = b"\x00" * 1024
        orig_key = storage.put_object(
            f"recordings/{rid}/original.wav",
            io.BytesIO(garbage),
            len(garbage),
            "audio/wav",
        )

        with pytest.raises(NormalizationError):
            normalize_audio(rid, orig_key, storage)

    def test_normalized_key_is_deterministic(self, storage) -> None:  # type: ignore[no-untyped-def]
        from app.services.normalize import normalize_audio

        rid = uuid.uuid4()
        wav_data = _make_wav(duration_s=0.2)
        orig_key = storage.put_object(
            f"recordings/{rid}/original.wav",
            io.BytesIO(wav_data),
            len(wav_data),
            "audio/wav",
        )

        k1 = normalize_audio(rid, orig_key, storage)
        k2 = normalize_audio(rid, orig_key, storage)
        assert k1 == k2

"""Contract tests for AudioSource port — M1-T3 / M2-T4."""

from __future__ import annotations

import io
import os
import struct
import uuid

import pytest

from app.core.ports import AudioPayload, AudioSource


def _make_wav_bytes(sample_rate: int = 16000) -> bytes:
    num_samples = sample_rate // 4
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return header + b"\x00" * data_size


def _try_file_source() -> tuple[str, AudioSource] | None:
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    try:
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("MINIO_ROOT_USER", "minioadmin"),
            aws_secret_access_key=os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"),
            region_name="us-east-1",
        )
        client.head_bucket(Bucket="test-contract")
    except Exception:
        try:
            client.create_bucket(Bucket="test-contract")  # type: ignore[possibly-undefined]
        except Exception:
            return None

    from app.adapters.audio.file_source import FileSource
    from app.services.storage import ObjectStorage

    storage = ObjectStorage(
        endpoint=endpoint,
        access_key=os.environ.get("MINIO_ROOT_USER", "minioadmin"),
        secret_key=os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"),
        bucket="test-contract",
    )
    storage.ensure_bucket()
    rid = uuid.uuid4()
    wav = _make_wav_bytes()
    key = storage.put_object(
        ObjectStorage.make_key(rid, "normalized", ".wav"),
        io.BytesIO(wav),
        len(wav),
        "audio/wav",
    )
    src = FileSource(
        storage=storage,
        normalized_key=key,
        manager_id=uuid.uuid4(),
        consent_flag=True,
    )
    return ("FileSource", src)


def _make_mic_source() -> tuple[str, AudioSource]:
    import uuid

    from app.adapters.audio.mic_source import MicSource
    src = MicSource(
        audio_data=_make_wav_bytes(),
        manager_id=uuid.uuid4(),
        consent_flag=True,
    )
    return ("MicSource", src)


def get_audio_source_impls() -> list[tuple[str, AudioSource]]:
    impls: list[tuple[str, AudioSource]] = []
    try:
        from app.adapters.audio.file_stub import FileStubSource
        impls.append(("FileStubSource", FileStubSource()))
    except ImportError:
        pass
    fs = _try_file_source()
    if fs:
        impls.append(fs)
    impls.append(_make_mic_source())
    return impls


_impls = get_audio_source_impls()
_ids = [label for label, _ in _impls]


@pytest.mark.contract
@pytest.mark.skipif(not _impls, reason="No AudioSource implementations registered yet")
@pytest.mark.parametrize("impl", [impl for _, impl in _impls], ids=_ids)
class TestAudioSourceContract:
    def test_fetch_returns_audio_payload(self, impl: AudioSource) -> None:
        payload = impl.fetch()
        assert isinstance(payload, AudioPayload)

    def test_payload_has_audio_data(self, impl: AudioSource) -> None:
        payload = impl.fetch()
        assert payload.audio_data, "audio_data must not be empty"

    def test_payload_has_valid_sample_rate(self, impl: AudioSource) -> None:
        payload = impl.fetch()
        assert payload.sample_rate > 0

    def test_payload_has_manager_id(self, impl: AudioSource) -> None:
        payload = impl.fetch()
        assert payload.manager_id is not None

    def test_payload_has_channel(self, impl: AudioSource) -> None:
        payload = impl.fetch()
        assert payload.channel

    def test_payload_has_consent_flag(self, impl: AudioSource) -> None:
        payload = impl.fetch()
        assert isinstance(payload.consent_flag, bool)

    def test_impl_satisfies_protocol(self, impl: AudioSource) -> None:
        assert isinstance(impl, AudioSource)

"""Unit tests for upload validation — M2-T2."""

from __future__ import annotations

import struct


def _make_wav(duration_s: float = 1.0, sample_rate: int = 16000) -> bytes:
    num_samples = int(duration_s * sample_rate)
    data_size = num_samples * 2  # 16-bit mono
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        1,  # mono
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size


def _make_mp3_stub() -> bytes:
    # MPEG sync word — 0xfffb recognized by libmagic as audio/mpeg
    return b"\xff\xfb\x90\x00" + b"\x00" * 200


def _make_ogg_stub() -> bytes:
    return b"OggS" + b"\x00" * 100


class TestValidateFormat:
    def test_wav_passes(self) -> None:
        from app.services.ingest import validate_upload

        validate_upload(_make_wav(), "recording.wav", max_size_bytes=50 * 1024 * 1024)

    def test_mp3_passes(self) -> None:
        from app.services.ingest import validate_upload

        validate_upload(_make_mp3_stub(), "recording.mp3", max_size_bytes=50 * 1024 * 1024)

    def test_ogg_rejected(self) -> None:
        from app.services.ingest import UploadValidationError, validate_upload

        with pytest.raises(UploadValidationError, match="format"):
            validate_upload(_make_ogg_stub(), "recording.ogg", max_size_bytes=50 * 1024 * 1024)

    def test_exe_rejected(self) -> None:
        from app.services.ingest import UploadValidationError, validate_upload

        exe_bytes = b"MZ" + b"\x00" * 100
        with pytest.raises(UploadValidationError, match="format"):
            validate_upload(exe_bytes, "malware.exe", max_size_bytes=50 * 1024 * 1024)

    def test_size_limit_enforced(self) -> None:
        from app.services.ingest import UploadValidationError, validate_upload

        big_wav = _make_wav()
        with pytest.raises(UploadValidationError, match="size"):
            validate_upload(big_wav, "recording.wav", max_size_bytes=10)

    def test_extension_mismatch_rejected(self) -> None:
        from app.services.ingest import UploadValidationError, validate_upload

        # wav bytes but .mp3 extension — magic check catches it
        with pytest.raises(UploadValidationError, match="format"):
            validate_upload(_make_wav(), "recording.mp3", max_size_bytes=50 * 1024 * 1024)

    def test_allowed_extensions_config_driven(self) -> None:
        from app.services.ingest import validate_upload

        # m4a magic bytes — ftyp box
        m4a_bytes = b"\x00\x00\x00\x20ftyp" + b"M4A " + b"\x00" * 100
        validate_upload(m4a_bytes, "recording.m4a", max_size_bytes=50 * 1024 * 1024)


import pytest  # noqa: E402

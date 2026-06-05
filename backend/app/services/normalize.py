"""ffmpeg-based audio normalization to target STT format (16 kHz mono wav)."""

from __future__ import annotations

import io
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.services.storage import ObjectStorage

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_EXT = ".wav"


class NormalizationError(RuntimeError):
    pass


def normalize_audio(
    recording_id: uuid.UUID,
    source_key: str,
    storage: ObjectStorage,
) -> str:
    """Download source from storage, normalize via ffmpeg, upload normalized file.

    Returns the storage key of the normalized file.
    Target format: 16 kHz, mono, PCM wav (whisper-ready).
    """
    norm_key = ObjectStorage.make_key(recording_id, "normalized", TARGET_EXT)

    raw = storage.get_object(source_key).read()

    with tempfile.TemporaryDirectory() as tmp:
        src_path = Path(tmp) / "input" / Path(source_key).name
        src_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.write_bytes(raw)

        dst_path = Path(tmp) / "normalized.wav"
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(src_path),
                "-ar", str(TARGET_SAMPLE_RATE),
                "-ac", str(TARGET_CHANNELS),
                "-f", "wav",
                str(dst_path),
            ],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise NormalizationError(
                f"ffmpeg failed (rc={result.returncode}): {result.stderr.decode()[:300]}"
            )

        norm_bytes = dst_path.read_bytes()

    storage.put_object(
        norm_key,
        io.BytesIO(norm_bytes),
        len(norm_bytes),
        "audio/wav",
    )
    return norm_key

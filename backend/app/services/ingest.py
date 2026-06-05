"""Upload ingestion: validation + storage orchestration."""

from __future__ import annotations

import magic

# magic MIME → allowed extensions (config-driven via ALLOWED_AUDIO_MIME_TO_EXT)
# Updated from providers.yaml/settings if needed; defaults cover MVP.
ALLOWED_MIME_TO_EXT: dict[str, set[str]] = {
    "audio/wav": {".wav"},
    "audio/x-wav": {".wav"},
    "audio/mpeg": {".mp3"},
    "audio/mp3": {".mp3"},
    "audio/mp4": {".m4a", ".mp4"},
    "video/mp4": {".m4a", ".mp4"},
    "audio/x-m4a": {".m4a"},
}


class UploadValidationError(ValueError):
    pass


def validate_upload(
    data: bytes,
    filename: str,
    max_size_bytes: int,
) -> None:
    """Validate audio upload by size, magic bytes, and extension."""
    if len(data) > max_size_bytes:
        raise UploadValidationError(
            f"File size {len(data)} exceeds limit {max_size_bytes} bytes (size)"
        )

    detected_mime = magic.from_buffer(data, mime=True)
    allowed = ALLOWED_MIME_TO_EXT.get(detected_mime)
    if allowed is None:
        raise UploadValidationError(
            f"Unsupported audio format: detected MIME '{detected_mime}' (format)"
        )

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed:
        raise UploadValidationError(
            f"Extension '{ext}' does not match detected MIME '{detected_mime}' (format)"
        )

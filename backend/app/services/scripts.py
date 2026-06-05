"""Script upload and parsing service — M6-T2."""

from __future__ import annotations

from pathlib import Path

_ALLOWED_EXTENSIONS = {".txt", ".md"}


def parse_script_content(filename: str, raw: bytes) -> str:
    """Validate format (txt/md) and return decoded content.

    Raises ValueError for unsupported extensions.
    """
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported script format '{ext}'. Allowed: .txt, .md")
    return raw.decode("utf-8", errors="replace").strip()

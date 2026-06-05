"""BadgeSource — perspective stub for physical audio badge device (not yet implemented)."""

from __future__ import annotations

from app.core.ports.audio_source import AudioPayload


class BadgeSource:
    """Stub for future physical badge audio source. Satisfies AudioSource protocol."""

    def fetch(self) -> AudioPayload:
        raise NotImplementedError("BadgeSource is not yet implemented (perspective stub)")

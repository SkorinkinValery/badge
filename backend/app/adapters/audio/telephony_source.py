"""TelephonySource — perspective stub for telephony integration (not yet implemented)."""

from __future__ import annotations

from app.core.ports.audio_source import AudioPayload


class TelephonySource:
    """Stub for future telephony audio source (A1/SIP). Satisfies AudioSource protocol."""

    def fetch(self) -> AudioPayload:
        raise NotImplementedError(
            "TelephonySource is not yet implemented (perspective stub)"
        )

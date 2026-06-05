"""Contract tests for STTEngine port — M1-T3."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.core.ports import AudioPayload, STTEngine
from tests.contract.helpers import assert_valid_transcript


def get_stt_impls() -> list[tuple[str, STTEngine]]:
    try:
        from app.adapters.stt.stub_stt import StubSTTEngine
        return [("StubSTTEngine", StubSTTEngine())]
    except ImportError:
        return []


_impls = get_stt_impls()
_ids = [label for label, _ in _impls]

_SAMPLE_PAYLOAD = AudioPayload(
    audio_data=b"\x00" * 100,
    sample_rate=16000,
    manager_id=uuid.uuid4(),
    channel="file",
    started_at=datetime.now(tz=UTC),
    consent_flag=True,
)


@pytest.mark.contract
@pytest.mark.skipif(not _impls, reason="No STTEngine implementations registered yet")
@pytest.mark.parametrize("impl", [impl for _, impl in _impls], ids=_ids)
class TestSTTEngineContract:
    def test_transcribe_returns_transcript(self, impl: STTEngine) -> None:
        from app.core.domain import Transcript
        result = impl.transcribe(_SAMPLE_PAYLOAD)
        assert isinstance(result, Transcript)

    def test_transcript_has_non_empty_segments(self, impl: STTEngine) -> None:
        result = impl.transcribe(_SAMPLE_PAYLOAD)
        assert result.segments

    def test_transcript_has_monotone_timecodes(self, impl: STTEngine) -> None:
        result = impl.transcribe(_SAMPLE_PAYLOAD)
        assert_valid_transcript(result)

    def test_transcript_has_detected_language(self, impl: STTEngine) -> None:
        result = impl.transcribe(_SAMPLE_PAYLOAD)
        assert result.detected_language

    def test_impl_satisfies_protocol(self, impl: STTEngine) -> None:
        assert isinstance(impl, STTEngine)

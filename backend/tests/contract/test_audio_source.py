"""Contract tests for AudioSource port — M1-T3."""

from __future__ import annotations

import pytest

from app.core.ports import AudioPayload, AudioSource


def get_audio_source_impls() -> list[tuple[str, AudioSource]]:
    """Return list of (label, impl) for parametrisation. Extended in T4."""
    try:
        from app.adapters.audio.file_stub import FileStubSource
        return [("FileStubSource", FileStubSource())]
    except ImportError:
        return []


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

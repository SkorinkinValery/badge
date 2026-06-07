"""Tests for the normalizing node — must load real audio, not a stub.

Regression coverage for the bug where `normalizing` always used FileStubSource
and stored a placeholder string, so STT silently transcribed silence regardless
of the uploaded/recorded audio (score always 0/100, empty transcript).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.core.domain.enums import RecordingStatus


def _make_state(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "recording_id": str(uuid.uuid4()),
        "status": RecordingStatus.UPLOADED.value,
        "stage_error": None,
        "retry": 0,
        "audio_path": "recordings/abc/original.mp3",
        "manager_id": "11111111-1111-1111-1111-111111111111",
        "consent_flag": True,
        "channel": "file",
        "audio_payload": None,
        "transcript": None,
        "analysis_result": None,
        "score": None,
        "verdict": None,
        "export_result": None,
    }
    state.update(overrides)
    return state


class FakeStorage:
    """Stand-in for ObjectStorage — normalize_audio is monkeypatched, so this
    object is only used as a non-None marker passed through to make_nodes."""


class TestNormalizingNodeWithStorage:
    def test_calls_normalize_audio_and_stores_normalized_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.pipeline import nodes as nodes_module

        captured: dict[str, Any] = {}

        def fake_normalize_audio(recording_id: uuid.UUID, source_key: str, storage: Any) -> str:
            captured["recording_id"] = recording_id
            captured["source_key"] = source_key
            return "recordings/abc/normalized.wav"

        monkeypatch.setattr(
            "app.services.normalize.normalize_audio", fake_normalize_audio
        )

        nodes = nodes_module.make_nodes(storage=FakeStorage())  # type: ignore[arg-type]
        state = _make_state()
        result = nodes["normalizing"](state)

        assert captured["source_key"] == "recordings/abc/original.mp3"
        assert str(captured["recording_id"]) == state["recording_id"]
        assert result["audio_payload"]["normalized_key"] == "recordings/abc/normalized.wav"
        assert result["audio_payload"]["manager_id"] == state["manager_id"]
        assert result["audio_payload"]["consent_flag"] is True
        assert result["audio_payload"]["channel"] == "file"
        assert result["status"] == RecordingStatus.NORMALIZING.value

    def test_normalization_error_fails_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.pipeline import nodes as nodes_module
        from app.services.normalize import NormalizationError

        def boom(recording_id: uuid.UUID, source_key: str, storage: Any) -> str:
            raise NormalizationError("ffmpeg failed (rc=1): bad input")

        monkeypatch.setattr("app.services.normalize.normalize_audio", boom)

        nodes = nodes_module.make_nodes(storage=FakeStorage())  # type: ignore[arg-type]
        state = _make_state()
        result = nodes["normalizing"](state)

        assert result["status"] == RecordingStatus.FAILED.value
        assert result["stage_error"] is not None
        assert "Normalization error" in result["stage_error"]

    def test_storage_key_not_found_fails_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.pipeline import nodes as nodes_module
        from app.services.storage import StorageKeyNotFoundError

        def boom(recording_id: uuid.UUID, source_key: str, storage: Any) -> str:
            raise StorageKeyNotFoundError("recordings/abc/original.mp3")

        monkeypatch.setattr("app.services.normalize.normalize_audio", boom)

        nodes = nodes_module.make_nodes(storage=FakeStorage())  # type: ignore[arg-type]
        state = _make_state()
        result = nodes["normalizing"](state)

        assert result["status"] == RecordingStatus.FAILED.value
        assert result["stage_error"] is not None


class TestNormalizingNodeWithoutStorage:
    def test_no_storage_uses_stub_branch(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        state = _make_state()
        result = nodes["normalizing"](state)

        assert result["audio_payload"]["normalized_key"] is None
        assert result["status"] == RecordingStatus.NORMALIZING.value

    def test_no_audio_path_uses_stub_branch(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(storage=FakeStorage())  # type: ignore[arg-type]
        state = _make_state(audio_path=None)
        result = nodes["normalizing"](state)

        assert result["audio_payload"]["normalized_key"] is None
        assert result["status"] == RecordingStatus.NORMALIZING.value


class TestNormalizingNodeFailureInjection:
    def test_fail_at_stage_sets_failed(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(fail_at_stage="normalizing")
        state = _make_state()
        result = nodes["normalizing"](state)

        assert result["status"] == RecordingStatus.FAILED.value
        assert result["stage_error"] is not None

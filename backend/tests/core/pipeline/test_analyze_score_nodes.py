"""Tests for analyzing + scoring nodes with Analyzer port DI — M4-T6."""

from __future__ import annotations

from typing import Any


def _make_state(recording_id: str | None = None) -> dict[str, Any]:
    import uuid
    from app.core.domain.enums import RecordingStatus

    return {
        "recording_id": recording_id or str(uuid.uuid4()),
        "status": RecordingStatus.TRANSCRIBING.value,
        "stage_error": None,
        "retry": 0,
        "audio_payload": None,
        "transcript": {
            "full_text": "Добрый день, чем могу помочь?",
            "detected_language": "ru",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Добрый день,"}],
        },
        "analysis_result": None,
        "score": None,
        "verdict": None,
        "export_result": None,
    }


class TestAnalyzingNode:
    def test_analyzing_sets_summary(self) -> None:
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(analyzer=StubAnalyzer())
        result = nodes["analyzing"](_make_state())
        assert result["analysis_result"] is not None
        assert result["analysis_result"]["summary"]

    def test_analyzing_sets_kpi_json(self) -> None:
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(analyzer=StubAnalyzer())
        result = nodes["analyzing"](_make_state())
        assert result["analysis_result"]["kpi_json"]

    def test_analyzing_sets_mode_baseline(self) -> None:
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(analyzer=StubAnalyzer())
        result = nodes["analyzing"](_make_state())
        assert result["analysis_result"]["mode"] == "baseline"

    def test_analyzer_exception_sets_failed(self) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.core.pipeline.nodes import make_nodes

        class BrokenAnalyzer:
            def analyze(self, transcript: object, script: object = None) -> None:  # type: ignore[override]
                raise RuntimeError("LLM crashed")

        nodes = make_nodes(analyzer=BrokenAnalyzer())  # type: ignore[arg-type]
        result = nodes["analyzing"](_make_state())
        assert result["status"] == RecordingStatus.FAILED.value
        assert result["stage_error"] is not None

    def test_injected_failure_sets_failed(self) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(fail_at_stage="analyzing")
        result = nodes["analyzing"](_make_state())
        assert result["status"] == RecordingStatus.FAILED.value

    def test_no_analyzer_uses_stub(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        result = nodes["analyzing"](_make_state())
        assert result["analysis_result"] is not None


class TestScoringNode:
    def _analyzed_state(self) -> dict[str, Any]:
        from app.adapters.analyzer.stub_analyzer import StubAnalyzer
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(analyzer=StubAnalyzer())
        return nodes["analyzing"](_make_state())

    def test_scoring_sets_score(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        state = self._analyzed_state()
        result = nodes["scoring"](state)
        assert result["score"] is not None
        assert isinstance(result["score"], float)

    def test_scoring_sets_verdict(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        state = self._analyzed_state()
        result = nodes["scoring"](state)
        assert result["verdict"] in ("+", "~", "-")

    def test_scoring_sets_weights_version(self) -> None:
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes()
        state = self._analyzed_state()
        result = nodes["scoring"](state)
        assert result["analysis_result"]["weights_version"]

    def test_scoring_injected_failure(self) -> None:
        from app.core.domain.enums import RecordingStatus
        from app.core.pipeline.nodes import make_nodes

        nodes = make_nodes(fail_at_stage="scoring")
        result = nodes["scoring"](_make_state())
        assert result["status"] == RecordingStatus.FAILED.value

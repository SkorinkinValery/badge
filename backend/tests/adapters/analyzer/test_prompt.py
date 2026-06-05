"""Unit tests for LLM prompt builder — M4-T2."""

from __future__ import annotations

import uuid

from app.core.domain.transcript import Segment, Transcript

_TRANSCRIPT = Transcript(
    id=uuid.uuid4(),
    recording_id=uuid.uuid4(),
    full_text="Добрый день, слушаю вас. Хорошо, понял.",
    segments=(
        Segment(start=0.0, end=2.0, text="Добрый день, слушаю вас."),
        Segment(start=2.0, end=4.0, text="Хорошо, понял."),
    ),
    detected_language="ru",
)


class TestPromptBuilderImport:
    def test_build_prompt_importable(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt  # noqa: F401


class TestBaselineMode:
    def test_baseline_prompt_contains_system_role(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt

        system, user = build_prompt(_TRANSCRIPT, script=None)
        assert len(system) > 0

    def test_baseline_prompt_contains_transcript(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt

        _, user = build_prompt(_TRANSCRIPT, script=None)
        assert "Добрый день" in user

    def test_baseline_prompt_contains_kpi_rubric(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        system, _ = build_prompt(_TRANSCRIPT, script=None)

        for kpi in cfg.kpis:
            if kpi.applies_to == "baseline":
                assert kpi.label in system, f"KPI label {kpi.label!r} missing from prompt"

    def test_baseline_prompt_contains_anchors_from_config(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        system, _ = build_prompt(_TRANSCRIPT, script=None)
        first_baseline = next(k for k in cfg.kpis if k.applies_to == "baseline")
        assert first_baseline.anchors[0] in system

    def test_baseline_prompt_requires_quote_per_kpi(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt

        system, _ = build_prompt(_TRANSCRIPT, script=None)
        assert "quote" in system.lower() or "цитата" in system.lower()

    def test_baseline_excludes_script_kpis(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        system, _ = build_prompt(_TRANSCRIPT, script=None)
        for kpi in cfg.kpis:
            if kpi.applies_to == "script":
                assert kpi.id not in system or "baseline" in system


class TestScriptMode:
    def test_script_mode_includes_script_content(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt

        script = "Этап 1: Приветствие\nЭтап 2: Выявление потребности"
        system, _ = build_prompt(_TRANSCRIPT, script=script)
        assert "Этап 1" in system

    def test_script_mode_includes_script_kpis(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt
        from app.config.kpi import load_kpi_config

        cfg = load_kpi_config()
        system, _ = build_prompt(_TRANSCRIPT, script="скрипт")
        for kpi in cfg.kpis:
            if kpi.applies_to == "script":
                assert kpi.label in system


class TestFewShot:
    def test_no_few_shot_does_not_raise(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt

        system, user = build_prompt(_TRANSCRIPT, script=None, few_shot=None)
        assert system
        assert user

    def test_few_shot_examples_included_when_provided(self) -> None:
        from app.adapters.analyzer.prompt import build_prompt

        examples = [{"transcript": "пример", "output": '{"greeting": {"value": 10}}'}]
        system, _ = build_prompt(_TRANSCRIPT, script=None, few_shot=examples)
        assert "пример" in system

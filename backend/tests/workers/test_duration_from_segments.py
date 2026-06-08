"""Unit tests for runner._duration_from_segments (pure, no DB)."""

from __future__ import annotations

from app.workers.runner import _duration_from_segments


def test_duration_is_max_segment_end() -> None:
    segments = [
        {"start": 0.0, "end": 2.5, "text": "a"},
        {"start": 2.5, "end": 7.25, "text": "b"},
        {"start": 7.25, "end": 5.0, "text": "out of order"},
    ]
    assert _duration_from_segments(segments) == 7.25


def test_duration_single_segment() -> None:
    assert _duration_from_segments([{"start": 0.0, "end": 1.0, "text": "x"}]) == 1.0


def test_duration_none_when_empty() -> None:
    assert _duration_from_segments([]) is None


def test_duration_none_when_not_a_list() -> None:
    assert _duration_from_segments(None) is None
    assert _duration_from_segments("nope") is None


def test_duration_ignores_segments_without_numeric_end() -> None:
    assert _duration_from_segments([{"start": 0.0, "text": "no end"}]) is None
    assert _duration_from_segments([{"end": None}]) is None


def test_duration_returns_float() -> None:
    result = _duration_from_segments([{"end": 3}])
    assert result == 3.0
    assert isinstance(result, float)

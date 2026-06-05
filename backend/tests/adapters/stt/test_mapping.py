"""Unit tests for whisper segments → domain Transcript mapping — M3-T3."""

from __future__ import annotations

import uuid


class _FakeSeg:
    """Minimal fake of faster_whisper segment."""

    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text


class TestSegmentMapping:
    def test_basic_mapping(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        raw = [_FakeSeg(0.0, 1.5, " Добрый день"), _FakeSeg(1.5, 3.0, " Чем помочь?")]
        recording_id = uuid.uuid4()
        result = map_segments_to_transcript(raw, recording_id, detected_language="ru")

        assert len(result.segments) == 2
        assert result.segments[0].start == 0.0
        assert result.segments[0].end == 1.5
        assert result.detected_language == "ru"

    def test_timecodes_monotone_and_non_negative(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        raw = [
            _FakeSeg(0.0, 2.0, "A"),
            _FakeSeg(2.0, 4.5, "B"),
            _FakeSeg(4.5, 7.0, "C"),
        ]
        result = map_segments_to_transcript(raw, uuid.uuid4(), detected_language="ru")
        prev_end = -1.0
        for seg in result.segments:
            assert seg.start >= 0
            assert seg.end > seg.start
            assert seg.end >= prev_end
            prev_end = seg.end

    def test_full_text_assembled_from_segments(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        raw = [_FakeSeg(0.0, 1.0, "Привет"), _FakeSeg(1.0, 2.0, "мир")]
        result = map_segments_to_transcript(raw, uuid.uuid4(), detected_language="ru")
        assert "Привет" in result.full_text
        assert "мир" in result.full_text

    def test_detected_language_propagated(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        raw = [_FakeSeg(0.0, 1.0, "Hello")]
        result = map_segments_to_transcript(raw, uuid.uuid4(), detected_language="en")
        assert result.detected_language == "en"

    def test_whitespace_normalized(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        raw = [_FakeSeg(0.0, 1.0, "  текст  ")]
        result = map_segments_to_transcript(raw, uuid.uuid4(), detected_language="ru")
        assert result.segments[0].text == "текст"

    def test_empty_segments_returns_empty_transcript(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        result = map_segments_to_transcript([], uuid.uuid4(), detected_language="ru")
        assert result.segments == ()
        assert result.full_text == ""

    def test_zero_duration_segments_skipped(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        raw = [
            _FakeSeg(1.0, 1.0, "zero"),   # end == start → skipped
            _FakeSeg(1.0, 2.0, "valid"),
        ]
        result = map_segments_to_transcript(raw, uuid.uuid4(), detected_language="ru")
        assert len(result.segments) == 1
        assert result.segments[0].text == "valid"

    def test_recording_id_set_correctly(self) -> None:
        from app.adapters.stt.mapping import map_segments_to_transcript

        rid = uuid.uuid4()
        result = map_segments_to_transcript([], rid, detected_language="ru")
        assert result.recording_id == rid

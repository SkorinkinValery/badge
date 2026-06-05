"""Unit tests for M7-T2: chunk buffer + near-realtime aggregation."""

from __future__ import annotations

import pytest

from app.services.mic_buffer import BufferOverflowError, ChunkBuffer


class TestChunkBuffer:
    def test_chunks_below_window_not_flushed(self) -> None:
        buf = ChunkBuffer(window_bytes=100, max_bytes=10_000)
        windows = buf.add(seq=0, data=b"x" * 50)
        assert windows == []

    def test_chunks_reach_window_returns_window(self) -> None:
        buf = ChunkBuffer(window_bytes=100, max_bytes=10_000)
        buf.add(seq=0, data=b"a" * 60)
        windows = buf.add(seq=1, data=b"b" * 60)
        assert len(windows) == 1
        assert len(windows[0]) >= 100

    def test_window_cleared_after_yield(self) -> None:
        buf = ChunkBuffer(window_bytes=50, max_bytes=10_000)
        buf.add(seq=0, data=b"x" * 60)
        # next small chunk should not trigger another window
        windows = buf.add(seq=1, data=b"y" * 10)
        assert windows == []

    def test_flush_returns_remaining_data(self) -> None:
        buf = ChunkBuffer(window_bytes=1000, max_bytes=10_000)
        buf.add(seq=0, data=b"z" * 200)
        remainder = buf.flush()
        assert remainder is not None
        assert len(remainder) == 200

    def test_flush_returns_none_when_empty(self) -> None:
        buf = ChunkBuffer(window_bytes=100, max_bytes=10_000)
        assert buf.flush() is None

    def test_flush_clears_buffer(self) -> None:
        buf = ChunkBuffer(window_bytes=1000, max_bytes=10_000)
        buf.add(seq=0, data=b"x" * 200)
        buf.flush()
        assert buf.flush() is None

    def test_multiple_windows_in_single_add(self) -> None:
        buf = ChunkBuffer(window_bytes=50, max_bytes=10_000)
        windows = buf.add(seq=0, data=b"x" * 200)
        assert len(windows) >= 3

    def test_skipped_seq_continues_without_error(self) -> None:
        buf = ChunkBuffer(window_bytes=1000, max_bytes=10_000)
        buf.add(seq=0, data=b"a" * 10)
        # seq 2 skipped — should not raise, just warn
        buf.add(seq=2, data=b"b" * 10)
        remainder = buf.flush()
        assert remainder == b"a" * 10 + b"b" * 10

    def test_duplicate_seq_ignored(self) -> None:
        buf = ChunkBuffer(window_bytes=1000, max_bytes=10_000)
        buf.add(seq=0, data=b"a" * 10)
        buf.add(seq=0, data=b"dup" * 10)  # duplicate ignored
        remainder = buf.flush()
        assert remainder == b"a" * 10

    def test_max_bytes_raises_on_overflow(self) -> None:
        buf = ChunkBuffer(window_bytes=1000, max_bytes=50)
        buf.add(seq=0, data=b"x" * 30)
        with pytest.raises(BufferOverflowError):
            buf.add(seq=1, data=b"y" * 30)

    def test_total_bytes_tracked(self) -> None:
        buf = ChunkBuffer(window_bytes=1000, max_bytes=10_000)
        buf.add(seq=0, data=b"x" * 100)
        buf.add(seq=1, data=b"y" * 100)
        assert buf.total_bytes == 200

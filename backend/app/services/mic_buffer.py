"""Chunk buffer for near-realtime microphone audio aggregation (M7-T2).

Accumulates WebSocket audio chunks into windows for STT processing.
Window size and session memory limit are config-driven.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

# Default config values — overridden by Settings in production
DEFAULT_WINDOW_BYTES = 32_000   # ~1 s of 16 kHz mono 16-bit PCM
DEFAULT_MAX_BYTES = 10_485_760  # 10 MB per session


class BufferOverflowError(RuntimeError):
    """Raised when a session buffer exceeds the configured memory limit."""


class ChunkBuffer:
    """Accumulates audio chunks and yields windows when threshold is reached.

    Handles out-of-order and duplicate seq numbers gracefully.
    Enforces a per-session memory cap to prevent resource exhaustion.
    """

    def __init__(
        self,
        window_bytes: int = DEFAULT_WINDOW_BYTES,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self._window_bytes = window_bytes
        self._max_bytes = max_bytes
        self._buffer = bytearray()
        self._seen_seqs: set[int] = set()
        self._total_bytes = 0

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    def add(self, seq: int, data: bytes) -> list[bytes]:
        """Add a chunk. Returns list of windows ready for STT (empty if below threshold)."""
        if seq in self._seen_seqs:
            logger.debug("mic_buffer.duplicate_seq_ignored", seq=seq)
            return []
        self._seen_seqs.add(seq)

        new_total = self._total_bytes + len(data)
        if new_total > self._max_bytes:
            raise BufferOverflowError(
                f"session buffer exceeded {self._max_bytes} bytes"
            )
        self._total_bytes = new_total
        self._buffer.extend(data)

        windows: list[bytes] = []
        while len(self._buffer) >= self._window_bytes:
            window = bytes(self._buffer[: self._window_bytes])
            windows.append(window)
            del self._buffer[: self._window_bytes]

        return windows

    def flush(self) -> bytes | None:
        """Flush remaining buffered data. Call on session stop.

        Returns remaining bytes or None if buffer is empty.
        Clears the buffer after flushing.
        """
        if not self._buffer:
            return None
        remainder = bytes(self._buffer)
        self._buffer.clear()
        return remainder

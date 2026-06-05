"""WS protocol DTOs for MicSource near-realtime capture.

Protocol version is carried in every `start` message for forward-compatibility
with future streaming/telephony sources.
"""

from __future__ import annotations

import base64
import json
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, ValidationError

PROTOCOL_VERSION = "1"


class MsgType:
    START = "start"
    CHUNK = "chunk"
    STOP = "stop"
    ACK = "ack"
    PARTIAL_TRANSCRIPT = "partial_transcript"
    ERROR = "error"


# ── Client → Server ──────────────────────────────────────────────────────────

class StartMsg(BaseModel):
    type: Literal["start"] = "start"
    protocol_version: str = PROTOCOL_VERSION
    manager_id: uuid.UUID
    consent_flag: bool
    channel: str = "mic"


class ChunkMsg(BaseModel):
    type: Literal["chunk"] = "chunk"
    seq: int
    data: str  # base64-encoded audio bytes

    def decode_data(self) -> bytes:
        return base64.b64decode(self.data)


class StopMsg(BaseModel):
    type: Literal["stop"] = "stop"


ClientMsg = Annotated[
    StartMsg | ChunkMsg | StopMsg,
    Field(discriminator="type"),
]

# ── Server → Client ──────────────────────────────────────────────────────────

class AckMsg(BaseModel):
    type: Literal["ack"] = "ack"
    seq: int | None = None
    message: str | None = None


class PartialTranscriptMsg(BaseModel):
    type: Literal["partial_transcript"] = "partial_transcript"
    text: str
    is_final: bool = False


class ErrorMsg(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


ServerMsg = Annotated[
    AckMsg | PartialTranscriptMsg | ErrorMsg,
    Field(discriminator="type"),
]

# ── Protocol helpers ─────────────────────────────────────────────────────────

class ProtocolError(ValueError):
    """Raised on invalid WS message type or ordering violation."""


def parse_client_msg(raw: str) -> StartMsg | ChunkMsg | StopMsg:
    """Parse and validate an incoming client message JSON string."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc

    try:
        from pydantic import TypeAdapter
        adapter: TypeAdapter[StartMsg | ChunkMsg | StopMsg] = TypeAdapter(ClientMsg)
        return adapter.validate_python(data)
    except (ValidationError, KeyError, TypeError) as exc:
        raise ProtocolError(f"unknown or malformed message type: {exc}") from exc


class SessionProtocol:
    """Tracks per-session WS state and enforces message ordering."""

    def __init__(self) -> None:
        self._started = False
        self._last_seq: int | None = None

    def validate(self, msg: StartMsg | ChunkMsg | StopMsg) -> None:
        """Raise ProtocolError on ordering or seq violations."""
        if isinstance(msg, StartMsg):
            self._started = True
            self._last_seq = None
        elif isinstance(msg, ChunkMsg):
            if not self._started:
                raise ProtocolError("chunk received before start")
            if self._last_seq is not None and msg.seq <= self._last_seq:
                raise ProtocolError(
                    f"non-monotonic seq: got {msg.seq}, last was {self._last_seq}"
                )
            self._last_seq = msg.seq
        elif isinstance(msg, StopMsg):
            if not self._started:
                raise ProtocolError("stop received before start")

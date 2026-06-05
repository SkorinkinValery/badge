"""Unit tests for M7-T1: WS protocol DTO serialisation/deserialisation."""

from __future__ import annotations

import base64
import json
import uuid

import pytest

from app.adapters.audio.mic_protocol import (
    PROTOCOL_VERSION,
    AckMsg,
    ChunkMsg,
    ErrorMsg,
    MsgType,
    PartialTranscriptMsg,
    ProtocolError,
    SessionProtocol,
    StartMsg,
    StopMsg,
    parse_client_msg,
)


class TestStartMsg:
    def test_serialisation_roundtrip(self) -> None:
        mid = uuid.uuid4()
        msg = StartMsg(manager_id=mid, consent_flag=True)
        raw = msg.model_dump_json()
        parsed = StartMsg.model_validate_json(raw)
        assert parsed.manager_id == mid
        assert parsed.consent_flag is True
        assert parsed.channel == "mic"
        assert parsed.type == MsgType.START

    def test_protocol_version_present(self) -> None:
        msg = StartMsg(manager_id=uuid.uuid4(), consent_flag=True)
        assert msg.protocol_version == PROTOCOL_VERSION

    def test_channel_defaults_to_mic(self) -> None:
        msg = StartMsg(manager_id=uuid.uuid4(), consent_flag=False)
        assert msg.channel == "mic"

    def test_consent_flag_required(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            StartMsg(manager_id=uuid.uuid4())  # type: ignore[call-arg]


class TestChunkMsg:
    def test_serialisation_roundtrip(self) -> None:
        raw_bytes = b"\x00\x01\x02\x03"
        encoded = base64.b64encode(raw_bytes).decode()
        msg = ChunkMsg(seq=1, data=encoded)
        raw = msg.model_dump_json()
        parsed = ChunkMsg.model_validate_json(raw)
        assert parsed.seq == 1
        assert parsed.decode_data() == raw_bytes

    def test_decode_data_returns_bytes(self) -> None:
        audio = b"\xff\xfe" * 16
        msg = ChunkMsg(seq=0, data=base64.b64encode(audio).decode())
        assert msg.decode_data() == audio

    def test_type_is_chunk(self) -> None:
        msg = ChunkMsg(seq=5, data=base64.b64encode(b"x").decode())
        assert msg.type == MsgType.CHUNK


class TestStopMsg:
    def test_serialisation_roundtrip(self) -> None:
        msg = StopMsg()
        raw = msg.model_dump_json()
        parsed = StopMsg.model_validate_json(raw)
        assert parsed.type == MsgType.STOP


class TestServerMessages:
    def test_ack_serialisation(self) -> None:
        msg = AckMsg(seq=3, message="ok")
        raw = msg.model_dump_json()
        parsed = AckMsg.model_validate_json(raw)
        assert parsed.seq == 3
        assert parsed.message == "ok"

    def test_ack_without_seq(self) -> None:
        msg = AckMsg()
        assert msg.seq is None

    def test_partial_transcript(self) -> None:
        msg = PartialTranscriptMsg(text="Добрый день", is_final=False)
        raw = msg.model_dump_json()
        parsed = PartialTranscriptMsg.model_validate_json(raw)
        assert parsed.text == "Добрый день"
        assert parsed.is_final is False

    def test_partial_transcript_final(self) -> None:
        msg = PartialTranscriptMsg(text="Итого", is_final=True)
        assert msg.is_final is True

    def test_error_message(self) -> None:
        msg = ErrorMsg(code="PROTOCOL_ERROR", message="chunk before start")
        raw = msg.model_dump_json()
        parsed = ErrorMsg.model_validate_json(raw)
        assert parsed.code == "PROTOCOL_ERROR"
        assert parsed.type == MsgType.ERROR


class TestParseClientMsg:
    def test_parse_start(self) -> None:
        raw = json.dumps(
            {"type": "start", "manager_id": str(uuid.uuid4()), "consent_flag": True}
        )
        msg = parse_client_msg(raw)
        assert isinstance(msg, StartMsg)

    def test_parse_chunk(self) -> None:
        raw = json.dumps(
            {"type": "chunk", "seq": 1, "data": base64.b64encode(b"x").decode()}
        )
        msg = parse_client_msg(raw)
        assert isinstance(msg, ChunkMsg)

    def test_parse_stop(self) -> None:
        raw = json.dumps({"type": "stop"})
        msg = parse_client_msg(raw)
        assert isinstance(msg, StopMsg)

    def test_invalid_type_raises(self) -> None:
        raw = json.dumps({"type": "unknown"})
        with pytest.raises(ProtocolError):
            parse_client_msg(raw)

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_msg("not json at all")


class TestSessionProtocol:
    def test_chunk_before_start_raises(self) -> None:
        proto = SessionProtocol()
        chunk = ChunkMsg(seq=0, data=base64.b64encode(b"x").decode())
        with pytest.raises(ProtocolError, match="before start"):
            proto.validate(chunk)

    def test_stop_before_start_raises(self) -> None:
        proto = SessionProtocol()
        with pytest.raises(ProtocolError, match="before start"):
            proto.validate(StopMsg())

    def test_start_then_chunk_ok(self) -> None:
        proto = SessionProtocol()
        proto.validate(StartMsg(manager_id=uuid.uuid4(), consent_flag=True))
        proto.validate(ChunkMsg(seq=0, data=base64.b64encode(b"a").decode()))
        proto.validate(ChunkMsg(seq=1, data=base64.b64encode(b"b").decode()))

    def test_non_monotonic_seq_raises(self) -> None:
        proto = SessionProtocol()
        proto.validate(StartMsg(manager_id=uuid.uuid4(), consent_flag=True))
        proto.validate(ChunkMsg(seq=5, data=base64.b64encode(b"x").decode()))
        with pytest.raises(ProtocolError, match="non-monotonic"):
            proto.validate(ChunkMsg(seq=5, data=base64.b64encode(b"y").decode()))

    def test_repeated_start_resets_session(self) -> None:
        proto = SessionProtocol()
        proto.validate(StartMsg(manager_id=uuid.uuid4(), consent_flag=True))
        proto.validate(ChunkMsg(seq=0, data=base64.b64encode(b"x").decode()))
        # Second start resets seq counter
        proto.validate(StartMsg(manager_id=uuid.uuid4(), consent_flag=True))
        proto.validate(ChunkMsg(seq=0, data=base64.b64encode(b"x").decode()))

    def test_start_then_stop_ok(self) -> None:
        proto = SessionProtocol()
        proto.validate(StartMsg(manager_id=uuid.uuid4(), consent_flag=True))
        proto.validate(StopMsg())

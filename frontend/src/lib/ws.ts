"use client";

import { useCallback, useRef, useState } from "react";
import { getToken } from "./auth";

export type RecordState = "idle" | "recording" | "stopping" | "done" | "error";

export interface UseRecordWsOptions {
  managerId: string;
  consentFlag: boolean;
  onPartialTranscript?: (text: string) => void;
  onFinalTranscript?: (text: string) => void;
  onRecordingCreated?: (recordingId: string) => void;
  onError?: (message: string) => void;
}

export interface UseRecordWsResult {
  state: RecordState;
  transcript: string;
  start: () => Promise<void>;
  stop: () => void;
  errorMessage: string | null;
}

const WS_BASE = (process.env.NEXT_PUBLIC_WS_URL ?? "").replace(/^http/, "ws");
const CHUNK_INTERVAL_MS = 500;

export function useRecordWs(options: UseRecordWsOptions): UseRecordWsResult {
  const { managerId, consentFlag, onPartialTranscript, onFinalTranscript, onRecordingCreated, onError } = options;

  const [state, setState] = useState<RecordState>("idle");
  const [transcript, setTranscript] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const seqRef = useRef(0);

  const _handleWsMessage = useCallback((event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data as string) as Record<string, unknown>;
      if (msg.type === "partial_transcript") {
        const text = msg.text as string;
        setTranscript((prev) => prev + (prev ? " " : "") + text);
        if (msg.is_final) {
          onFinalTranscript?.(text);
          setState("done");
        } else {
          onPartialTranscript?.(text);
        }
      } else if (msg.type === "ack") {
        const message = msg.message as string | undefined;
        if (message?.startsWith("recording ")) {
          const rid = message.split(" ")[1];
          onRecordingCreated?.(rid);
        }
      } else if (msg.type === "error") {
        const errMsg = msg.message as string;
        setErrorMessage(errMsg);
        setState("error");
        onError?.(errMsg);
      }
    } catch {
      // ignore parse errors
    }
  }, [onPartialTranscript, onFinalTranscript, onRecordingCreated, onError]);

  const start = useCallback(async () => {
    if (state !== "idle") return;
    setErrorMessage(null);
    setTranscript("");
    seqRef.current = 0;

    // Request microphone access
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setErrorMessage("Не удалось получить доступ к микрофону");
      setState("error");
      return;
    }

    // Connect WebSocket — token in query param (WS cannot send Authorization header)
    const token = getToken();
    const ws = new WebSocket(`${WS_BASE}/api/ws/mic?token=${token ?? ""}`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          type: "start",
          manager_id: managerId,
          consent_flag: consentFlag,
        })
      );
    };

    ws.onmessage = _handleWsMessage;

    ws.onerror = () => {
      setErrorMessage("Ошибка соединения");
      setState("error");
    };

    ws.onclose = () => {
      if (state === "recording" || state === "stopping") {
        setState("done");
      }
    };

    // Start MediaRecorder
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    recorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data.size === 0 || ws.readyState !== WebSocket.OPEN) return;
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = (reader.result as string).split(",")[1];
        ws.send(
          JSON.stringify({
            type: "chunk",
            seq: seqRef.current++,
            data: base64,
          })
        );
      };
      reader.readAsDataURL(event.data);
    };

    recorder.start(CHUNK_INTERVAL_MS);
    setState("recording");
  }, [state, managerId, consentFlag, _handleWsMessage]);

  const stop = useCallback(() => {
    if (state !== "recording") return;
    setState("stopping");

    recorderRef.current?.stop();

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "stop" }));
    }
  }, [state]);

  return { state, transcript, start, stop, errorMessage };
}

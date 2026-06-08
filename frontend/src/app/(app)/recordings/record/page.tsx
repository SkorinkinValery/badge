"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";
import { useRecordWs } from "@/lib/ws";
import type { Manager } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Button, Field, Waveform, inputClass } from "@/components/ui";

export default function RecordPage() {
  const router = useRouter();
  const [managers, setManagers] = useState<Manager[]>([]);
  const [managerId, setManagerId] = useState("");
  const [consentFlag, setConsentFlag] = useState(false);
  const [recordingId, setRecordingId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    fetch("/api/managers", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setManagers(data as Manager[]))
      .catch(() => {});
  }, []);

  const { state, start, stop, errorMessage } = useRecordWs({
    managerId: managerId ?? "",
    consentFlag,
    onRecordingCreated: (rid) => setRecordingId(rid),
  });

  const isRecording = state === "recording";
  const isStopping = state === "stopping";
  const canStart = consentFlag && !!managerId && state === "idle";

  // Once the recording is created (ack) and the session reaches a terminal
  // "done" state (final transcript or WS close), jump to the pipeline view —
  // same flow as after a file upload. Using an effect (not the WS callback)
  // avoids the stale-closure on recordingId captured at start() time.
  useEffect(() => {
    if (state === "done" && recordingId) {
      router.push(`/recordings/${recordingId}`);
    }
  }, [state, recordingId, router]);

  useEffect(() => {
    if (!isRecording) {
      setElapsed(0);
      return;
    }
    const id = setInterval(() => setElapsed((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, [isRecording]);

  const activeManagers = managers.filter((m) => m.is_active);
  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <Page title="Запись с микрофона" kicker="Студия">
      <div className="max-w-2xl">
        {/* studio panel */}
        <div className="flex flex-col gap-6 border border-border-2 bg-black px-7 py-[30px]">
          <div className="flex items-center justify-between">
            <span
              className="mono text-[11px] uppercase tracking-[.1em]"
              style={{ color: isRecording ? "var(--accent)" : "var(--muted)" }}
            >
              {isRecording ? "● ИДЁТ ЗАПИСЬ" : "○ ГОТОВ К ЗАПИСИ"}
            </span>
            <span
              className="num"
              style={{ fontSize: 30, color: isRecording ? "var(--text)" : "var(--muted-2)" }}
            >
              {mm}:{ss}
            </span>
          </div>

          <Waveform active={isRecording} />

          <Field label="Менеджер" required>
            <select
              className={inputClass}
              value={managerId}
              onChange={(e) => setManagerId(e.target.value)}
              disabled={isRecording || isStopping}
            >
              <option value="">Выберите менеджера</option>
              {activeManagers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name} ({m.position})
                </option>
              ))}
            </select>
          </Field>

          <label
            className="flex cursor-pointer items-start gap-[11px] text-[13px] text-muted"
            style={{ opacity: isRecording ? 0.5 : 1 }}
          >
            <input
              type="checkbox"
              checked={consentFlag}
              onChange={(e) => setConsentFlag(e.target.checked)}
              disabled={isRecording || isStopping}
              className="mt-[2px] flex-none accent-accent"
            />
            <span>
              Я уведомил собеседника о записи разговора и получил согласие в соответствии с
              политикой компании.
            </span>
          </label>

          {errorMessage && (
            <div role="alert" className="border border-danger/40 bg-danger/[0.08] px-[13px] py-[10px] text-[12.5px] text-danger">
              {errorMessage}
            </div>
          )}

          <div className="flex gap-3">
            {!isRecording && !isStopping && (
              <Button full disabled={!canStart} onClick={() => void start()}>
                ● Начать запись
              </Button>
            )}
            {isRecording && (
              <Button variant="solid" full onClick={stop}>
                ■ Остановить запись
              </Button>
            )}
            {isStopping && (
              <div className="mono w-full py-2 text-center text-[13px] text-muted">
                Запись завершена, открываем анализ…
              </div>
            )}
          </div>

          <p className="text-center text-[12px] text-muted-2">
            После остановки запись отправляется на расшифровку и анализ — вы перейдёте на страницу
            разговора автоматически.
          </p>
        </div>
      </div>
    </Page>
  );
}

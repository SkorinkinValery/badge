"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";
import type { Manager } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Page } from "@/components/app-shell/Page";
import { Button, Field, HexMotif, PixelH, inputClass } from "@/components/ui";

export default function UploadRecordingPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [managers, setManagers] = useState<Manager[]>([]);
  const [managerId, setManagerId] = useState("");
  const [consentFlag, setConsentFlag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/managers", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setManagers(data as Manager[]))
      .catch(() => {});
  }, []);

  const activeManagers = managers.filter((m) => m.is_active);
  const canSubmit = !!managerId && consentFlag && !!file && !submitting;

  async function handleUpload() {
    if (!managerId || !file) return;
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("manager_id", managerId);
      form.append("consent_flag", String(consentFlag));
      const resp = await fetch("/api/uploads", {
        method: "POST",
        headers: authHeaders() as Record<string, string>,
        body: form,
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setErrorMessage(body?.detail ?? `Ошибка загрузки (HTTP ${resp.status})`);
        return;
      }
      router.push(`/recordings/${body.recording_id}`);
    } catch {
      setErrorMessage("Не удалось загрузить запись");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Page title="Загрузить запись" kicker="Импорт аудио">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.3fr_1fr]">
        <div>
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
            }}
            className={cn(
              "cursor-pointer border-2 border-dashed px-6 py-14 text-center transition-colors",
              drag ? "border-accent bg-accent-soft" : "border-border-2 bg-bg",
            )}
          >
            <div className="mb-[18px] flex justify-center">
              <HexMotif size={84} />
            </div>
            <PixelH size={24}>Перетащите аудио сюда</PixelH>
            <p className="mt-[10px] text-[13.5px] text-muted">или нажмите, чтобы выбрать файл</p>
            <p className="mono mt-[14px] text-[11px] text-muted-2">MP3 · WAV · M4A · OGG · до 200 МБ</p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="audio/*"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file && (
            <div className="mt-[18px] flex items-center justify-between gap-3 border border-border px-[18px] py-[14px]">
              <span className="mono text-[13px]">{file.name}</span>
              <button onClick={() => setFile(null)} className="text-[14px] text-muted-2" aria-label="Убрать файл">
                ✕
              </button>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-[18px] self-start border border-border bg-bg p-[22px]">
          <span className="mono text-[11px] uppercase tracking-[.08em] text-muted">Параметры анализа</span>
          <Field label="Менеджер" required>
            <select
              className={inputClass}
              value={managerId}
              onChange={(e) => setManagerId(e.target.value)}
              disabled={submitting}
            >
              <option value="">Выберите менеджера</option>
              {activeManagers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name} ({m.position})
                </option>
              ))}
            </select>
          </Field>

          <label className="flex cursor-pointer items-start gap-[10px] text-[13px] text-muted">
            <input
              type="checkbox"
              checked={consentFlag}
              onChange={(e) => setConsentFlag(e.target.checked)}
              disabled={submitting}
              className="mt-[2px] flex-none accent-accent"
            />
            <span>Согласие клиента на запись (consent_flag) получено в соответствии с политикой компании.</span>
          </label>

          {errorMessage && (
            <div role="alert" className="border border-danger/40 bg-danger/[0.08] px-[13px] py-[10px] text-[12.5px] text-danger">
              {errorMessage}
            </div>
          )}

          <Button full disabled={!canSubmit} onClick={() => void handleUpload()}>
            {submitting ? "Загрузка…" : "Загрузить запись"}
          </Button>
        </div>
      </div>
    </Page>
  );
}

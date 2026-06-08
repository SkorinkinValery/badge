"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { Script } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import { Button, Field, inputClass, toast } from "@/components/ui";

export default function NewManagerPage() {
  const router = useRouter();
  const admin = useIsAdmin();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [fullName, setFullName] = useState("");
  const [position, setPosition] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [defaultScriptId, setDefaultScriptId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/scripts", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setScripts(data as Script[]))
      .catch(() => {});
  }, []);

  if (admin === false) return <Forbidden />;

  const activeScripts = scripts.filter((s) => s.is_active);
  const canSubmit = !!fullName.trim() && !!position.trim() && !submitting;

  async function handleCreate() {
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const resp = await fetch("/api/managers", {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName.trim(),
          position: position.trim(),
          device_id: deviceId.trim() || null,
          default_script_id: defaultScriptId || null,
        }),
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setErrorMessage(body?.detail ?? `Ошибка создания (HTTP ${resp.status})`);
        return;
      }
      toast("Менеджер создан", "success");
      router.push("/admin/managers");
    } catch {
      setErrorMessage("Не удалось создать менеджера");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Page
      crumb={[{ label: "Менеджеры", href: "/admin/managers" }, { label: "Новый" }]}
      title="Новый менеджер"
      kicker="Администрирование"
    >
      <div className="max-w-[560px]">
        <div className="flex flex-col gap-[18px] border border-border bg-bg p-[26px]">
          <Field label="ФИО" required>
            <input
              className={inputClass}
              placeholder="Иванов Иван Иванович"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={submitting}
            />
          </Field>
          <Field label="Должность" required>
            <input
              className={inputClass}
              placeholder="Менеджер продаж"
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              disabled={submitting}
            />
          </Field>
          <Field label="Device ID" hint="Опционально">
            <input
              className={inputClass}
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              disabled={submitting}
            />
          </Field>
          <Field label="Скрипт по умолчанию">
            <select
              className={inputClass}
              value={defaultScriptId}
              onChange={(e) => setDefaultScriptId(e.target.value)}
              disabled={submitting}
            >
              <option value="">Не выбран</option>
              {activeScripts.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>

          {errorMessage && (
            <div role="alert" className="border border-danger/40 bg-danger/[0.08] px-[13px] py-[10px] text-[12.5px] text-danger">
              {errorMessage}
            </div>
          )}
        </div>

        <div className="mt-5 flex gap-[10px]">
          <Button variant="ghost" onClick={() => router.push("/admin/managers")}>
            Отмена
          </Button>
          <Button disabled={!canSubmit} onClick={() => void handleCreate()}>
            Создать менеджера
          </Button>
        </div>
      </div>
    </Page>
  );
}

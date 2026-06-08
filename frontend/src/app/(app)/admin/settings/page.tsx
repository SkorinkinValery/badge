"use client";

import { useEffect, useState } from "react";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { CrmSettings } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import { Button, Field, inputClass } from "@/components/ui";

export default function SettingsPage() {
  const admin = useIsAdmin();
  const [settings, setSettings] = useState<CrmSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!admin) return;
    fetch("/api/admin/settings", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setSettings(data as CrmSettings))
      .catch(() => setError("Не удалось загрузить настройки"));
  }, [admin]);

  if (admin === false) return <Forbidden />;

  function setParam(key: string, value: string) {
    setSettings((s) => (s ? { ...s, params: { ...s.params, [key]: value } } : s));
  }

  async function handleSave() {
    if (!settings) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const resp = await fetch("/api/admin/settings", {
        method: "PUT",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ active_crm: settings.active_crm, params: settings.params }),
      });
      if (!resp.ok) {
        const body = await resp.json();
        setError((body as { detail?: string }).detail ?? "Ошибка сохранения");
      } else {
        setSaved(true);
      }
    } catch {
      setError("Сетевая ошибка");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Page title="Настройки CRM-экспорта" kicker="Администрирование">
      {settings && (
        <div className="flex max-w-[560px] flex-col gap-[18px] border border-border bg-bg p-[26px]">
          <Field label="Активный провайдер">
            <select
              className={inputClass}
              value={settings.active_crm}
              onChange={(e) =>
                setSettings((s) => (s ? { ...s, active_crm: e.target.value, params: {} } : s))
              }
            >
              {settings.available_providers.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </Field>

          {settings.active_crm === "google_sheets" && (
            <>
              <Field label="Spreadsheet ID">
                <input className={inputClass} value={settings.params.spreadsheet_id ?? ""} onChange={(e) => setParam("spreadsheet_id", e.target.value)} />
              </Field>
              <Field label="Название листа">
                <input className={inputClass} value={settings.params.worksheet_name ?? ""} onChange={(e) => setParam("worksheet_name", e.target.value)} />
              </Field>
            </>
          )}
          {settings.active_crm === "webhook" && (
            <Field label="URL вебхука">
              <input className={inputClass} value={settings.params.url ?? ""} onChange={(e) => setParam("url", e.target.value)} />
            </Field>
          )}
          {settings.active_crm === "bitrix24" && (
            <Field label="Webhook URL Bitrix24">
              <input className={inputClass} value={settings.params.webhook_url ?? ""} onChange={(e) => setParam("webhook_url", e.target.value)} />
            </Field>
          )}

          {error && (
            <div role="alert" className="border border-danger/40 bg-danger/[0.08] px-[13px] py-[10px] text-[12.5px] text-danger">
              {error}
            </div>
          )}
          {saved && (
            <div className="border border-success/40 bg-success/[0.08] px-[13px] py-[10px] text-[12.5px] text-success">
              Настройки сохранены
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Сохранение…" : "Сохранить"}
            </Button>
            <span className="text-[12px] text-muted-2">Изменения вступают в силу немедленно</span>
          </div>
        </div>
      )}
    </Page>
  );
}

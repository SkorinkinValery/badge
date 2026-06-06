"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Container,
  Group,
  Select,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { authHeaders } from "@/lib/auth";

interface CrmSettings {
  active_crm: string;
  available_providers: string[];
  params: Record<string, string>;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<CrmSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/admin/settings", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setSettings(data as CrmSettings))
      .catch(() => setError("Не удалось загрузить настройки"));
  }, []);

  if (!settings) return null;

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const resp = await fetch("/api/admin/settings", {
        method: "PUT",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          active_crm: settings.active_crm,
          params: settings.params,
        }),
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
  };

  const setParam = (key: string, value: string) => {
    setSettings((s) => s ? { ...s, params: { ...s.params, [key]: value } } : s);
  };

  return (
    <Container mt={40} maw={560}>
      <Title order={2} mb="lg">
        Настройки CRM-экспорта
      </Title>

      <Select
        label="Активный провайдер"
        data={settings.available_providers}
        value={settings.active_crm}
        onChange={(v) =>
          setSettings((s) => s ? { ...s, active_crm: v ?? "json", params: {} } : s)
        }
        mb="md"
      />

      {settings.active_crm === "google_sheets" && (
        <>
          <TextInput
            label="Spreadsheet ID"
            placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
            value={settings.params.spreadsheet_id ?? ""}
            onChange={(e) => setParam("spreadsheet_id", e.currentTarget.value)}
            mb="sm"
          />
          <TextInput
            label="Название листа"
            placeholder="Результаты"
            value={settings.params.worksheet_name ?? ""}
            onChange={(e) => setParam("worksheet_name", e.currentTarget.value)}
            mb="sm"
          />
        </>
      )}

      {settings.active_crm === "webhook" && (
        <TextInput
          label="URL вебхука"
          placeholder="https://example.com/hook"
          value={settings.params.url ?? ""}
          onChange={(e) => setParam("url", e.currentTarget.value)}
          mb="sm"
        />
      )}

      {settings.active_crm === "bitrix24" && (
        <TextInput
          label="Webhook URL Bitrix24"
          placeholder="https://portal.bitrix24.ru/rest/1/<token>/"
          value={settings.params.webhook_url ?? ""}
          onChange={(e) => setParam("webhook_url", e.currentTarget.value)}
          mb="sm"
        />
      )}

      {error && (
        <Alert color="red" mb="sm">
          {error}
        </Alert>
      )}
      {saved && (
        <Alert color="green" mb="sm">
          Настройки сохранены
        </Alert>
      )}

      <Group mt="md">
        <Button onClick={handleSave} loading={saving}>
          Сохранить
        </Button>
        <Text size="sm" c="dimmed">
          Изменения вступают в силу немедленно (до перезапуска сервиса)
        </Text>
      </Group>
    </Container>
  );
}

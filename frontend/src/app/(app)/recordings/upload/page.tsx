"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  Button,
  Checkbox,
  Container,
  FileInput,
  Select,
  Stack,
  Title,
} from "@mantine/core";
import { authHeaders } from "@/lib/auth";

interface Manager {
  id: string;
  full_name: string;
  position: string;
  is_active: boolean;
}

export default function UploadRecordingPage() {
  const router = useRouter();
  const [managers, setManagers] = useState<Manager[]>([]);
  const [managerId, setManagerId] = useState<string | null>(null);
  const [consentFlag, setConsentFlag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/managers", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setManagers(data as Manager[]))
      .catch(() => {});
  }, []);

  const managerOptions = managers
    .filter((m) => m.is_active)
    .map((m) => ({ value: m.id, label: `${m.full_name} (${m.position})` }));

  const canSubmit = !!managerId && consentFlag && !!file && !submitting;

  const handleUpload = async () => {
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
  };

  return (
    <Container size="sm" py="xl">
      <Title order={2} mb="md">
        Загрузка записи разговора
      </Title>

      <Stack gap="md">
        <Select
          label="Менеджер"
          placeholder="Выберите менеджера"
          data={managerOptions}
          value={managerId}
          onChange={setManagerId}
          disabled={submitting}
        />

        <Checkbox
          label="Согласие клиента на запись (consent_flag)"
          checked={consentFlag}
          onChange={(e) => setConsentFlag(e.currentTarget.checked)}
          disabled={submitting}
        />

        <FileInput
          label="Аудиофайл"
          placeholder="Выберите файл"
          accept="audio/*"
          value={file}
          onChange={setFile}
          disabled={submitting}
          clearable
        />

        {errorMessage && (
          <Alert color="red" title="Ошибка">
            {errorMessage}
          </Alert>
        )}

        <Button
          disabled={!canSubmit}
          loading={submitting}
          onClick={() => void handleUpload()}
        >
          Загрузить запись
        </Button>
      </Stack>
    </Container>
  );
}

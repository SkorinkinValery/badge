"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  Badge,
  Box,
  Button,
  Checkbox,
  Container,
  Group,
  Loader,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { getToken } from "@/lib/auth";
import { useRecordWs } from "@/lib/ws";

interface Manager {
  id: string;
  full_name: string;
  position: string;
  is_active: boolean;
}

export default function RecordPage() {
  const router = useRouter();
  const [managers, setManagers] = useState<Manager[]>([]);
  const [managerId, setManagerId] = useState<string | null>(null);
  const [consentFlag, setConsentFlag] = useState(false);
  const [recordingId, setRecordingId] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetch("/api/managers", {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((data) => setManagers(data as Manager[]))
      .catch(() => {});
  }, [router]);

  const { state, transcript, start, stop, errorMessage } = useRecordWs({
    managerId: managerId ?? "",
    consentFlag,
    onRecordingCreated: (rid) => setRecordingId(rid),
    onFinalTranscript: () => {
      if (recordingId) {
        router.push(`/recordings/${recordingId}`);
      }
    },
  });

  const isRecording = state === "recording";
  const isStopping = state === "stopping";
  const canStart = consentFlag && !!managerId && state === "idle";

  const managerOptions = managers
    .filter((m) => m.is_active)
    .map((m) => ({ value: m.id, label: `${m.full_name} (${m.position})` }));

  return (
    <Container size="sm" py="xl">
      <Title order={2} mb="md">
        Запись звонка с микрофона
      </Title>

      <Stack gap="md">
        <Select
          label="Менеджер"
          placeholder="Выберите менеджера"
          data={managerOptions}
          value={managerId}
          onChange={setManagerId}
          disabled={isRecording || isStopping}
        />

        <Checkbox
          label="Согласие клиента на запись (consent_flag)"
          checked={consentFlag}
          onChange={(e) => setConsentFlag(e.currentTarget.checked)}
          disabled={isRecording || isStopping}
        />

        {errorMessage && (
          <Alert color="red" title="Ошибка">
            {errorMessage}
          </Alert>
        )}

        <Group>
          {!isRecording && !isStopping && (
            <Button
              color="red"
              disabled={!canStart}
              onClick={() => void start()}
            >
              Начать запись
            </Button>
          )}

          {isRecording && (
            <>
              <Badge color="red" size="lg">
                Запись идёт
              </Badge>
              <Button variant="outline" onClick={stop}>
                Остановить запись
              </Button>
            </>
          )}

          {isStopping && (
            <Group>
              <Loader size="sm" />
              <Text>Завершение записи…</Text>
            </Group>
          )}
        </Group>

        {transcript && (
          <Box>
            <Text fw={500} mb={4}>
              Транскрипт (real-time):
            </Text>
            <Textarea
              value={transcript}
              readOnly
              minRows={4}
              autosize
            />
          </Box>
        )}

        {state === "done" && !recordingId && (
          <Alert color="green">Запись завершена. Обработка…</Alert>
        )}
      </Stack>
    </Container>
  );
}

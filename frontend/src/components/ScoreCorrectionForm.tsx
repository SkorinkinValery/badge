"use client";

import { useState } from "react";
import { Alert, Button, Group, NumberInput, Stack, Text } from "@mantine/core";
import { authHeaders } from "@/lib/auth";

interface Props {
  recordingId: string;
  currentScore: number | null;
  autoScore: number | null;
  currentVerdict: string | null;
  onSaved: () => void;
}

export default function ScoreCorrectionForm({
  recordingId,
  currentScore,
  autoScore,
  onSaved,
}: Props) {
  const [score, setScore] = useState<number | "">(currentScore ?? "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    setError(null);
    setLoading(true);
    try {
      const resp = await fetch(`/api/recordings/${recordingId}/analysis`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ score: score === "" ? null : score }),
      });
      const body = await resp.json();
      if (!resp.ok) throw new Error(body?.detail ?? "Ошибка сохранения");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Stack>
      {autoScore !== null && (
        <Text size="sm" c="dimmed">
          Исходная оценка: {autoScore}
        </Text>
      )}
      {error && (
        <Alert role="alert" color="red" title="Ошибка">
          {error}
        </Alert>
      )}
      <NumberInput
        label="Оценка"
        min={0}
        max={100}
        value={score}
        onChange={(v) => setScore(v as number | "")}
      />
      <Group>
        <Button loading={loading} onClick={handleSave}>
          Сохранить
        </Button>
      </Group>
    </Stack>
  );
}

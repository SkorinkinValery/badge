"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Alert,
  Badge,
  Card,
  Container,
  Group,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { authHeaders } from "@/lib/auth";

interface Segment {
  start: number;
  end: number;
  text: string;
}

interface KpiEntry {
  value: number;
  quote: string;
  comment: string;
}

interface Transcript {
  full_text: string;
  segments: Segment[];
  detected_language: string;
}

interface Analysis {
  summary: string;
  kpi_json: Record<string, KpiEntry | number>;
  score: number | null;
  auto_score: number | null;
  verdict: string | null;
  mode: string;
  weights_version: string | null;
}

interface Recording {
  id: string;
  channel: string;
  status: string;
  created_at: string;
  stage_error: string | null;
  retention_until: string | null;
}

interface KpiMeta {
  id: string;
  label: string;
  type: string;
  weight: number;
  applies_to: string;
  include_in_score: boolean;
}

const VERDICT_COLOR: Record<string, string> = { "+": "green", "~": "yellow", "-": "red" };
const VERDICT_LABEL: Record<string, string> = {
  "+": "Хорошо",
  "~": "Удовлетворительно",
  "-": "Требует внимания",
};

// Fetch JSON only on a 2xx response; otherwise null (so a 404 "not found"
// payload never leaks into the UI and crashes Object.entries).
async function fetchOk<T>(url: string, headers: HeadersInit): Promise<T | null> {
  try {
    const r = await fetch(url, { headers });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

function kpiValue(entry: KpiEntry | number): number {
  return typeof entry === "object" ? entry.value : entry;
}

export default function RecordingCard() {
  const params = useParams();
  const id = params?.id as string;

  const [recording, setRecording] = useState<Recording | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [kpiMeta, setKpiMeta] = useState<KpiMeta[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const h = authHeaders();
    Promise.all([
      fetchOk<Recording>(`/api/recordings/${id}`, h),
      fetchOk<Transcript>(`/api/recordings/${id}/transcript`, h),
      fetchOk<Analysis>(`/api/recordings/${id}/analysis`, h),
      fetchOk<KpiMeta[]>(`/api/kpi`, h),
    ]).then(([rec, t, a, k]) => {
      setRecording(rec);
      setTranscript(t && Array.isArray(t.segments) ? t : null);
      setAnalysis(a && a.kpi_json ? a : null);
      setKpiMeta(Array.isArray(k) ? k : []);
      setLoaded(true);
    });
  }, [id]);

  const metaById = new Map(kpiMeta.map((m) => [m.id, m]));
  // Order KPI rows by the rubric (kpi.yaml) when we have it; otherwise as-is.
  const kpiEntries: Array<[string, KpiEntry | number]> = analysis
    ? (kpiMeta.length > 0
        ? kpiMeta
            .filter((m) => m.id in analysis.kpi_json)
            .map((m) => [m.id, analysis.kpi_json[m.id]] as [string, KpiEntry | number])
        : Object.entries(analysis.kpi_json))
    : [];

  return (
    <Container mt={40} mb={60}>
      <Title order={2} mb="md">Карточка разговора</Title>
      <Stack>
        {recording && (
          <Card withBorder>
            <Group gap="xl">
              <Group gap="xs">
                <Text fw={600}>Статус:</Text>
                <Badge color={recording.status === "done" ? "green" : recording.status === "failed" ? "red" : "blue"}>
                  {recording.status}
                </Badge>
              </Group>
              <Group gap="xs">
                <Text fw={600}>Канал:</Text>
                <Text>{recording.channel}</Text>
              </Group>
              <Group gap="xs">
                <Text fw={600}>Дата:</Text>
                <Text>{new Date(recording.created_at).toLocaleString("ru-RU")}</Text>
              </Group>
              <Group gap="xs">
                <Text fw={600}>Хранить до:</Text>
                <Text>
                  {recording.retention_until
                    ? new Date(recording.retention_until).toLocaleString("ru-RU")
                    : "—"}
                </Text>
              </Group>
            </Group>
          </Card>
        )}

        {recording?.status === "failed" && recording.stage_error && (
          <Alert color="red" title="Ошибка обработки">
            {recording.stage_error}
          </Alert>
        )}

        {analysis ? (
          <Card withBorder>
            <Group justify="space-between" mb="md">
              <Group gap="xs" align="baseline">
                <Text fw={600}>Итоговый балл:</Text>
                <Text fz={32} fw={700}>{analysis.score ?? "—"}</Text>
                <Text c="dimmed">/ 100</Text>
              </Group>
              {analysis.verdict && (
                <Group gap="xs" wrap="nowrap">
                  <Badge size="xl" color={VERDICT_COLOR[analysis.verdict] ?? "gray"}>
                    {analysis.verdict}
                  </Badge>
                  <Text fw={600}>{VERDICT_LABEL[analysis.verdict] ?? ""}</Text>
                </Group>
              )}
            </Group>

            {analysis.summary && (
              <>
                <Text fw={600} mb={4}>Резюме:</Text>
                <Text mb="md">{analysis.summary}</Text>
              </>
            )}

            <Text fw={600} mb="xs">KPI — чек-лист по этапам разговора:</Text>
            <Table striped withTableBorder>
              <thead>
                <tr>
                  <th>Этап / признак</th>
                  <th>Оценка</th>
                  <th>Цитата</th>
                  <th>Комментарий</th>
                </tr>
              </thead>
              <tbody>
                {kpiEntries.map(([key, entry]) => {
                  const meta = metaById.get(key);
                  const e = typeof entry === "object" ? (entry as KpiEntry) : null;
                  const val = kpiValue(entry);
                  const isFact = meta?.type === "fact";
                  return (
                    <tr key={key}>
                      <td>{meta?.label ?? key}</td>
                      <td>
                        {isFact ? (
                          <Group gap={4} wrap="nowrap">
                            <ThemeIcon size="sm" radius="xl" color={val >= 10 ? "green" : "red"}>
                              {val >= 10 ? "✓" : "✗"}
                            </ThemeIcon>
                            <Text size="sm">{val >= 10 ? "да" : "нет"}</Text>
                          </Group>
                        ) : (
                          <Badge color={val >= 8 ? "green" : val >= 5 ? "yellow" : "red"}>
                            {val} / 10
                          </Badge>
                        )}
                      </td>
                      <td>{e?.quote ?? ""}</td>
                      <td>{e?.comment ?? ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          </Card>
        ) : (
          recording && recording.status !== "failed" && (
            <Alert color="gray" title="Анализ ещё не готов">
              KPI и оценка появятся после завершения обработки записи (статус «done»).
            </Alert>
          )
        )}

        {transcript ? (
          <Card withBorder>
            <Text fw={600} mb="xs">Транскрипт:</Text>
            <Text mb="md">{transcript.full_text}</Text>
            <Text fw={600} mb="xs">Сегменты:</Text>
            <Stack gap={4}>
              {transcript.segments.map((seg, i) => (
                <Group key={i} gap="xs">
                  <Text size="xs" c="dimmed">[{seg.start.toFixed(1)}–{seg.end.toFixed(1)}]</Text>
                  <Text size="sm">{seg.text}</Text>
                </Group>
              ))}
            </Stack>
          </Card>
        ) : (
          loaded && recording && (
            <Alert color="gray" title="Транскрипт недоступен">
              Текст разговора ещё не сформирован.
            </Alert>
          )
        )}
      </Stack>
    </Container>
  );
}

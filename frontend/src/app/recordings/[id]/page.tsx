"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Badge,
  Card,
  Container,
  Group,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { authHeaders, getToken } from "@/lib/auth";

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

export default function RecordingCard() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;

  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    const h = authHeaders();
    Promise.all([
      fetch(`/api/recordings/${id}/transcript`, { headers: h }).then((r) => r.json()),
      fetch(`/api/recordings/${id}/analysis`, { headers: h }).then((r) => r.json()),
    ]).then(([t, a]) => {
      setTranscript(t as Transcript);
      setAnalysis(a as Analysis);
    });
  }, [id, router]);

  return (
    <Container mt={40}>
      <Title order={2} mb="md">Запись {id}</Title>
      <Stack>
        {analysis && (
          <Card withBorder>
            <Group mb="xs">
              <Text fw={600}>Оценка:</Text>
              <Text>{analysis.score}</Text>
              <Badge color={analysis.verdict === "+" ? "green" : analysis.verdict === "~" ? "yellow" : "red"}>
                {analysis.verdict}
              </Badge>
            </Group>
            <Text fw={600} mb="xs">Резюме:</Text>
            <Text mb="md">{analysis.summary}</Text>
            <Text fw={600} mb="xs">KPI:</Text>
            <Table>
              <thead><tr><th>KPI</th><th>Оценка</th><th>Цитата</th><th>Комментарий</th></tr></thead>
              <tbody>
                {Object.entries(analysis.kpi_json).map(([key, entry]) => {
                  const e = typeof entry === "object" ? entry as KpiEntry : null;
                  return (
                    <tr key={key}>
                      <td>{key}</td>
                      <td>{e ? e.value : String(entry)}</td>
                      <td>{e?.quote ?? ""}</td>
                      <td>{e?.comment ?? ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          </Card>
        )}
        {transcript && (
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
        )}
      </Stack>
    </Container>
  );
}

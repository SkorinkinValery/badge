"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Badge,
  Container,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { authHeaders, getToken } from "@/lib/auth";

interface Recording {
  id: string;
  manager_id: string;
  channel: string;
  status: string;
  consent_flag: boolean;
  created_at: string;
  audio_path: string | null;
  stage_error: string | null;
  retention_until: string | null;
}

const STATUS_COLOR: Record<string, string> = {
  done: "green",
  queued: "blue",
  failed: "red",
  normalizing: "yellow",
  transcribing: "cyan",
  analyzing: "indigo",
  scoring: "violet",
  exporting: "orange",
};

export default function RecordingsPage() {
  const router = useRouter();
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetch("/api/recordings", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setRecordings(data as Recording[]);
        setLoaded(true);
      });
  }, [router]);

  if (!loaded) return null;

  if (recordings.length === 0) {
    return (
      <Container mt={40}>
        <Title order={2} mb="md">Записи</Title>
        <Text>Нет записей</Text>
      </Container>
    );
  }

  return (
    <Container mt={40}>
      <Title order={2} mb="md">Записи</Title>
      <Table striped highlightOnHover>
        <thead>
          <tr>
            <th>ID</th>
            <th>Статус</th>
            <th>Дата</th>
            <th>Канал</th>
          </tr>
        </thead>
        <tbody>
          {recordings.map((r) => (
            <tr
              key={r.id}
              style={{ cursor: "pointer" }}
              onClick={() => router.push(`/recordings/${r.id}`)}
            >
              <td>{r.id.slice(0, 8)}</td>
              <td>
                <Badge color={STATUS_COLOR[r.status] ?? "gray"}>{r.status}</Badge>
              </td>
              <td>{new Date(r.created_at).toLocaleString("ru-RU")}</td>
              <td>{r.channel}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
}

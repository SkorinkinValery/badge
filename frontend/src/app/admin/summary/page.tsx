"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Badge,
  Card,
  Container,
  Grid,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { authHeaders, getToken } from "@/lib/auth";

interface Manager {
  id: string;
  full_name: string;
  position: string;
  is_active: boolean;
  device_id: string | null;
  default_script_id: string | null;
}

interface KpiStat {
  kpi_id: string;
  label: string;
  fulfilled_pct: number;
}

interface Summary {
  manager_id: string;
  date: string;
  total_recordings: number;
  total_duration_s: number;
  avg_duration_s: number;
  avg_score: number | null;
  kpi_stats: KpiStat[];
  violations: string[];
  top_issues: string[];
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}м ${s}с`;
}

export default function SummaryPage() {
  const router = useRouter();
  const [managers, setManagers] = useState<Manager[]>([]);
  const [managerId, setManagerId] = useState<string | null>(null);
  const [date, setDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetch("/api/managers", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data: Manager[]) => {
        setManagers(data);
        if (data.length > 0) setManagerId(data[0].id);
        setLoaded(true);
      });
  }, [router]);

  useEffect(() => {
    if (!managerId || !date) return;
    const params = new URLSearchParams({ manager_id: managerId, date });
    fetch(`/api/admin/summary?${params}`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setSummary(data as Summary));
  }, [managerId, date]);

  if (!loaded) return null;

  const managerOptions = managers.map((m) => ({
    value: m.id,
    label: m.full_name,
  }));

  return (
    <Container mt={40}>
      <Title order={2} mb="md">Дневная сводка</Title>

      <Group mb="lg" align="flex-end">
        <Select
          label="Менеджер"
          placeholder="Выберите менеджера"
          data={managerOptions}
          value={managerId}
          onChange={setManagerId}
          style={{ minWidth: 260 }}
        />
        <TextInput
          label="Дата"
          type="date"
          value={date}
          onChange={(e) => setDate(e.currentTarget.value)}
        />
      </Group>

      {summary && (
        <Stack gap="md">
          <SimpleGrid cols={4}>
            <Card withBorder>
              <Text size="sm" c="dimmed">Звонков</Text>
              <Text fw={700} size="xl">{summary.total_recordings}</Text>
            </Card>
            <Card withBorder>
              <Text size="sm" c="dimmed">Общая длительность</Text>
              <Text fw={700} size="xl">{formatDuration(summary.total_duration_s)}</Text>
            </Card>
            <Card withBorder>
              <Text size="sm" c="dimmed">Средняя длительность</Text>
              <Text fw={700} size="xl">{formatDuration(summary.avg_duration_s)}</Text>
            </Card>
            <Card withBorder>
              <Text size="sm" c="dimmed">Средний балл</Text>
              <Text fw={700} size="xl">
                {summary.avg_score !== null ? `${summary.avg_score.toFixed(1)}%` : "—"}
              </Text>
            </Card>
          </SimpleGrid>

          {summary.kpi_stats.length > 0 && (
            <Card withBorder>
              <Title order={4} mb="sm">Выполнение KPI</Title>
              <Table>
                <thead>
                  <tr>
                    <th>Показатель</th>
                    <th>% выполнения</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.kpi_stats.map((k) => (
                    <tr key={k.kpi_id}>
                      <td>{k.label}</td>
                      <td>
                        <Badge color={k.fulfilled_pct >= 70 ? "green" : k.fulfilled_pct >= 40 ? "yellow" : "red"}>
                          {k.fulfilled_pct.toFixed(0)}%
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card>
          )}

          {summary.violations.length > 0 && (
            <Card withBorder>
              <Title order={4} mb="sm">Нарушения регламента</Title>
              <Group gap="xs">
                {summary.violations.map((v) => (
                  <Badge key={v} color="red">{v}</Badge>
                ))}
              </Group>
            </Card>
          )}

          {summary.top_issues.length > 0 && (
            <Card withBorder>
              <Title order={4} mb="sm">Топ проблемных пунктов</Title>
              <Stack gap="xs">
                {summary.top_issues.map((issue, i) => (
                  <Text key={i} size="sm">{i + 1}. {issue}</Text>
                ))}
              </Stack>
            </Card>
          )}
        </Stack>
      )}

      {summary && summary.total_recordings === 0 && (
        <Text c="dimmed" mt="md">Нет данных за выбранный день</Text>
      )}
    </Container>
  );
}

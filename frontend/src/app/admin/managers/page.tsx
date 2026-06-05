"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Badge,
  Button,
  Container,
  Group,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { authHeaders, getToken } from "@/lib/auth";

interface Manager {
  id: string;
  full_name: string;
  position: string;
  device_id: string | null;
  is_active: boolean;
  default_script_id: string | null;
}

export default function ManagersPage() {
  const router = useRouter();
  const [managers, setManagers] = useState<Manager[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetch("/api/managers", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setManagers(data as Manager[]);
        setLoaded(true);
      });
  }, [router]);

  if (!loaded) return null;

  return (
    <Container mt={40}>
      <Group justify="space-between" mb="md">
        <Title order={2}>Менеджеры</Title>
        <Button onClick={() => router.push("/admin/managers/new")}>
          Добавить менеджера
        </Button>
      </Group>

      {managers.length === 0 ? (
        <Text>Нет менеджеров</Text>
      ) : (
        <Table striped highlightOnHover>
          <thead>
            <tr>
              <th>ФИО</th>
              <th>Должность</th>
              <th>Device ID</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {managers.map((m) => (
              <tr
                key={m.id}
                style={{ cursor: "pointer" }}
                onClick={() => router.push(`/admin/managers/${m.id}`)}
              >
                <td>{m.full_name}</td>
                <td>{m.position}</td>
                <td>{m.device_id ?? "—"}</td>
                <td>
                  <Badge color={m.is_active ? "green" : "gray"}>
                    {m.is_active ? "Активен" : "Неактивен"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Badge,
  Button,
  Container,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { authHeaders } from "@/lib/auth";

interface Script {
  id: string;
  name: string;
  is_active: boolean;
  active_version_id: string | null;
}

export default function ScriptsPage() {
  const router = useRouter();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const loadScripts = () => {
    fetch("/api/scripts", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setScripts(data as Script[]);
        setLoaded(true);
      });
  };

  useEffect(() => {
    loadScripts();
  }, []);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !newName) return;
    const form = new FormData();
    form.append("name", newName);
    form.append("file", file);
    await fetch("/api/scripts", {
      method: "POST",
      headers: authHeaders() as Record<string, string>,
      body: form,
    });
    setModalOpen(false);
    setNewName("");
    loadScripts();
  };

  if (!loaded) return null;

  return (
    <Container mt={40}>
      <Group justify="space-between" mb="md">
        <Title order={2}>Скрипты</Title>
        <Button onClick={() => setModalOpen(true)}>Новый скрипт</Button>
      </Group>

      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Загрузить скрипт"
      >
        <Stack>
          <TextInput
            label="Название скрипта"
            value={newName}
            onChange={(e) => setNewName(e.currentTarget.value)}
          />
          <input ref={fileRef} type="file" accept=".txt,.md" />
          <Button onClick={handleUpload}>Загрузить</Button>
        </Stack>
      </Modal>

      {scripts.length === 0 ? (
        <Text>Нет скриптов</Text>
      ) : (
        <Table striped highlightOnHover>
          <thead>
            <tr>
              <th>Название</th>
              <th>Активная версия</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {scripts.map((s) => (
              <tr
                key={s.id}
                style={{ cursor: "pointer" }}
                onClick={() => router.push(`/admin/scripts/${s.id}`)}
              >
                <td>{s.name}</td>
                <td>
                  {s.active_version_id ? (
                    <Badge color="blue">Активная версия</Badge>
                  ) : (
                    <Text size="sm" c="dimmed">Нет</Text>
                  )}
                </td>
                <td>
                  <Badge color={s.is_active ? "green" : "gray"}>
                    {s.is_active ? "Активен" : "Архив"}
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

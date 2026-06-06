"use client";

import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Container,
  Group,
  PasswordInput,
  Select,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { authHeaders } from "@/lib/auth";

interface User {
  id: string;
  login: string;
  role: string;
  is_active: boolean;
}

const ROLES = [
  { value: "admin", label: "admin" },
  { value: "viewer", label: "viewer" },
];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loaded, setLoaded] = useState(false);

  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<string>("viewer");
  const [error, setError] = useState<string | null>(null);

  const reload = () => {
    fetch("/api/admin/users", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setUsers(data as User[]);
        setLoaded(true);
      });
  };

  useEffect(reload, []);

  const createUser = async () => {
    setError(null);
    const resp = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ login, password, role }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setError(body?.detail ?? `Ошибка ${resp.status}`);
      return;
    }
    setLogin("");
    setPassword("");
    setRole("viewer");
    reload();
  };

  const toggleActive = async (u: User) => {
    await fetch(`/api/admin/users/${u.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    reload();
  };

  const removeUser = async (u: User) => {
    await fetch(`/api/admin/users/${u.id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    reload();
  };

  if (!loaded) return null;

  return (
    <Container mt={40}>
      <Title order={2} mb="md">Пользователи</Title>

      <Group align="flex-end" mb="lg">
        <TextInput
          label="Логин"
          value={login}
          onChange={(e) => setLogin(e.currentTarget.value)}
        />
        <PasswordInput
          label="Пароль"
          value={password}
          onChange={(e) => setPassword(e.currentTarget.value)}
        />
        <Select
          label="Роль"
          data={ROLES}
          value={role}
          onChange={(v) => setRole(v ?? "viewer")}
          allowDeselect={false}
        />
        <Button onClick={createUser} disabled={!login || !password}>
          Создать
        </Button>
      </Group>
      {error && <Text c="red" mb="md">{error}</Text>}

      {users.length === 0 ? (
        <Text>Нет пользователей</Text>
      ) : (
        <Table striped highlightOnHover>
          <thead>
            <tr>
              <th>Логин</th>
              <th>Роль</th>
              <th>Статус</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.login}</td>
                <td>
                  <Badge color={u.role === "admin" ? "blue" : "gray"}>{u.role}</Badge>
                </td>
                <td>
                  <Badge color={u.is_active ? "green" : "gray"}>
                    {u.is_active ? "Активен" : "Неактивен"}
                  </Badge>
                </td>
                <td>
                  <Group gap="xs">
                    <Button size="xs" variant="light" onClick={() => toggleActive(u)}>
                      {u.is_active ? "Деактивировать" : "Активировать"}
                    </Button>
                    <Button size="xs" color="red" variant="light" onClick={() => removeUser(u)}>
                      Удалить
                    </Button>
                  </Group>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  );
}

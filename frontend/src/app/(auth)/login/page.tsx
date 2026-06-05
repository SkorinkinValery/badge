"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button, Container, PasswordInput, Stack, TextInput, Title } from "@mantine/core";
import { storeToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const form = new URLSearchParams({ username: login, password });
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString(),
      });
      const body = await resp.json();
      if (!resp.ok) throw new Error(body?.detail ?? "Ошибка входа");
      storeToken(body.access_token as string);
      router.push("/recordings");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Container size={400} mt={100}>
      <Title order={2} mb="md">Вход</Title>
      <form onSubmit={handleSubmit}>
        <Stack>
          {error && (
            <Alert role="alert" color="red" title="Ошибка">
              {error}
            </Alert>
          )}
          <TextInput
            label="Логин"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            required
          />
          <PasswordInput
            label="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" loading={loading}>
            Войти
          </Button>
        </Stack>
      </form>
    </Container>
  );
}

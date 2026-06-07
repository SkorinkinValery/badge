"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AppShell,
  Button,
  Group,
  NavLink,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { clearToken, getRole, getToken } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setIsAdmin(getRole() === "admin");
    setReady(true);
  }, [router]);

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  if (!ready) return null;

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: "sm" }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={4}>Аудиобейдж</Title>
          <Button variant="subtle" size="sm" onClick={handleLogout}>
            Выйти
          </Button>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <Stack gap={4}>
          <Text size="xs" fw={600} c="dimmed" tt="uppercase" px={8} py={4}>
            Звонки
          </Text>
          <NavLink
            component={Link}
            href="/recordings"
            label="Записи"
          />
          <NavLink
            component={Link}
            href="/recordings/record"
            label="Запись с микрофона"
          />

          {isAdmin && (
            <>
              <NavLink
                component={Link}
                href="/recordings/upload"
                label="Загрузить запись"
              />

              <Text size="xs" fw={600} c="dimmed" tt="uppercase" px={8} py={4} mt={8}>
                Администрирование
              </Text>
              <NavLink
                component={Link}
                href="/admin/users"
                label="Пользователи"
              />
              <NavLink
                component={Link}
                href="/admin/managers"
                label="Менеджеры"
              />
              <NavLink
                component={Link}
                href="/admin/scripts"
                label="Скрипты"
              />
              <NavLink
                component={Link}
                href="/admin/summary"
                label="Дневная сводка"
              />
              <NavLink
                component={Link}
                href="/admin/settings"
                label="Настройки"
              />
            </>
          )}
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>{children}</AppShell.Main>
    </AppShell>
  );
}

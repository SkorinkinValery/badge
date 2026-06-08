"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { storeToken } from "@/lib/auth";
import { Button, Field, HexLogo, HexMotif, Kicker, PixelH, inputClass } from "@/components/ui";

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
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="gridlines flex min-h-screen items-center justify-center bg-bg p-6">
      <div className="absolute left-7 top-6 flex items-center gap-[11px]">
        <HexLogo size={24} />
        <span className="disp text-[23px]">Аудиобейдж</span>
      </div>

      <div className="w-[404px] max-w-full">
        <div className="mb-[26px] flex justify-center">
          <HexMotif size={92} />
        </div>
        <div className="mb-[10px] flex justify-center">
          <Kicker>AI-анализ звонков</Kicker>
        </div>
        <PixelH size={34} className="mb-[30px] text-center">
          Вход в систему
        </PixelH>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-[18px] border border-border-2 bg-surface px-[26px] py-7"
        >
          {error && (
            <div
              role="alert"
              className="border border-danger/40 bg-danger/[0.08] px-[13px] py-[10px] text-[12.5px] text-danger"
            >
              {error}
            </div>
          )}
          <Field label="Логин" required>
            <input
              className={inputClass}
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              autoComplete="username"
            />
          </Field>
          <Field label="Пароль" required>
            <input
              className={inputClass}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </Field>
          <Button type="submit" full disabled={loading}>
            {loading ? "Вход…" : "Войти →"}
          </Button>
        </form>
      </div>
    </div>
  );
}

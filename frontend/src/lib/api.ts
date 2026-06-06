import { authHeaders, clearToken } from "./auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers ?? {}),
    },
  });
  if (!resp.ok) {
    if (resp.status === 401) {
      clearToken();
      window.location.href = "/login";
    }
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<{ access_token: string }> {
  const form = new URLSearchParams({ username, password });
  const resp = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  const body = await resp.json();
  if (!resp.ok) throw new Error(body?.detail ?? "Login failed");
  return body as { access_token: string };
}

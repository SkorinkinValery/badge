const TOKEN_KEY = "badge_token";

export function storeToken(token: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(TOKEN_KEY, token);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function decodeClaims(): Record<string, unknown> | null {
  try {
    const token = getToken();
    if (!token) return null;
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    return JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

export function getRole(): string | null {
  const role = decodeClaims()?.role;
  return typeof role === "string" ? role : null;
}

/** Logged-in user's login (JWT `sub` claim). */
export function getLogin(): string | null {
  const sub = decodeClaims()?.sub;
  return typeof sub === "string" ? sub : null;
}

export function isAdmin(): boolean {
  return getRole() === "admin";
}

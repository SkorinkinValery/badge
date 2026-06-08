"use client";

import { useEffect, useState } from "react";
import { isAdmin } from "./auth";

/** null = not yet determined (SSR/first paint), then true/false. */
export function useIsAdmin(): boolean | null {
  const [admin, setAdmin] = useState<boolean | null>(null);
  useEffect(() => setAdmin(isAdmin()), []);
  return admin;
}

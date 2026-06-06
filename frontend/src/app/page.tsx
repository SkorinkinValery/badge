"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  // Один хоп: незалогиненного сразу на /login, залогиненного — на /recordings.
  // Так убираем промежуточный редирект / → /recordings → /login.
  useEffect(() => {
    router.replace(getToken() ? "/recordings" : "/login");
  }, [router]);
  return null;
}

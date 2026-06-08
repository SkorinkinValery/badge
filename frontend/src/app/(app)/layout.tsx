"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearToken, getLogin, getRole, getToken } from "@/lib/auth";
import { Toaster } from "@/components/ui";
import { Header } from "@/components/app-shell/Header";
import { Sidebar } from "@/components/app-shell/Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [role, setRole] = useState<string | null>(null);
  const [login, setLogin] = useState<string | null>(null);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setRole(getRole());
    setLogin(getLogin());
    setReady(true);
  }, [router]);

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  if (!ready) return null;
  const isAdmin = role === "admin";

  return (
    <div>
      <Header
        login={login}
        role={role}
        onBurger={() => setDrawer(true)}
        onLogout={handleLogout}
      />
      <div className="flex" style={{ minHeight: "calc(100vh - var(--header-h))" }}>
        <div className="hidden md:block">
          <Sidebar isAdmin={isAdmin} />
        </div>
        <main className="gridlines min-w-0 flex-1">{children}</main>
      </div>

      {drawer && (
        <div className="fixed inset-0 z-[120] flex md:hidden">
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => setDrawer(false)}
          />
          <div className="relative h-full w-[260px] max-w-[80%] overflow-y-auto">
            <div className="flex justify-end bg-black px-4 py-3">
              <button
                onClick={() => setDrawer(false)}
                className="text-[20px] text-muted"
                aria-label="Закрыть"
              >
                ✕
              </button>
            </div>
            <Sidebar isAdmin={isAdmin} mobile onNav={() => setDrawer(false)} />
          </div>
        </div>
      )}

      <Toaster />
    </div>
  );
}

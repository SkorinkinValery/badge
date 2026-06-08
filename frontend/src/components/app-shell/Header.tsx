"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";
import { Button, HexLogo } from "@/components/ui";

export function Header({
  login,
  role,
  onBurger,
  onLogout,
}: {
  login: string | null;
  role: string | null;
  onBurger: () => void;
  onLogout: () => void;
}) {
  const isAdmin = role === "admin";
  return (
    <header
      className="sticky top-0 z-[90] flex items-center gap-4 border-b border-border bg-black px-5"
      style={{ height: "var(--header-h)" }}
    >
      <button onClick={onBurger} className="p-[6px] md:hidden" aria-label="Меню">
        <svg width="20" height="20" viewBox="0 0 20 20">
          <rect y="3" width="20" height="2" fill="#fff" />
          <rect y="9" width="20" height="2" fill="#fff" />
          <rect y="15" width="20" height="2" fill="#fff" />
        </svg>
      </button>

      <Link href="/dashboard" className="flex items-center gap-[11px]">
        <HexLogo size={24} />
        <span className="disp text-[23px] tracking-[.02em]">Аудиобейдж</span>
      </Link>

      <div className="flex-1" />

      <div className="flex items-center gap-3">
        {login && (
          <div className="mono hidden text-right text-[11px] text-muted-2 sm:block">
            {login}
          </div>
        )}
        {role && (
          <span
            className={cn(
              "mono border px-[10px] py-[5px] text-[10px] uppercase tracking-[.08em]",
              isAdmin ? "border-accent text-accent" : "border-border-2 text-muted",
            )}
          >
            {role}
          </span>
        )}
        <Button variant="ghost" sm onClick={onLogout}>
          Выйти
        </Button>
      </div>
    </header>
  );
}

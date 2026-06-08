"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { NAV, NavIcon } from "./icons";

export function Sidebar({
  isAdmin,
  mobile,
  onNav,
}: {
  isAdmin: boolean;
  mobile?: boolean;
  onNav?: () => void;
}) {
  const pathname = usePathname();
  const items = NAV.flatMap((s) => s.items);
  const activeR = items
    .filter((it) => pathname === it.r || pathname.startsWith(it.r + "/"))
    .sort((a, b) => b.r.length - a.r.length)[0]?.r;

  return (
    <nav
      className={cn(
        "flex flex-col gap-1 bg-black py-[18px]",
        mobile
          ? "h-auto w-full"
          : "sticky w-sidebar flex-none overflow-y-auto border-r border-border",
      )}
      style={
        mobile
          ? undefined
          : { top: "var(--header-h)", height: "calc(100vh - var(--header-h))" }
      }
    >
      {NAV.filter((s) => !s.admin || isAdmin).map((sec) => (
        <div key={sec.sec} className="mb-[14px]">
          <div className="mono px-[22px] pb-[10px] pt-[6px] text-[9.5px] uppercase tracking-[.16em] text-muted-2">
            {sec.sec}
          </div>
          {sec.items
            .filter((it) => !it.admin || isAdmin)
            .map((it) => {
              const on = it.r === activeR;
              return (
                <Link
                  key={it.r}
                  href={it.r}
                  onClick={onNav}
                  className={cn(
                    "flex w-full items-center gap-3 border-l-2 px-[22px] py-[9px] text-left text-[13.5px] transition-colors",
                    on
                      ? "border-accent bg-accent-soft text-accent"
                      : "border-transparent text-muted hover:text-text",
                  )}
                >
                  <NavIcon type={it.icon} />
                  {it.label}
                </Link>
              );
            })}
        </div>
      ))}
    </nav>
  );
}

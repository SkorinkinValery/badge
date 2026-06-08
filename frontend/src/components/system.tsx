"use client";

import Link from "next/link";
import { Button, PixelH } from "@/components/ui";

export function SysScreen({
  code,
  title,
  desc,
  href = "/dashboard",
  cta = "На дашборд",
  danger,
}: {
  code: string;
  title: string;
  desc: string;
  href?: string;
  cta?: string;
  danger?: boolean;
}) {
  return (
    <div className="gridlines flex min-h-[70vh] flex-col items-center justify-center px-6 py-16 text-center">
      <div
        className="disp"
        style={{ fontSize: 120, lineHeight: 0.8, color: danger ? "var(--danger)" : "var(--accent)" }}
      >
        {code}
      </div>
      <PixelH size={30} className="mt-[10px]">
        {title}
      </PixelH>
      <p className="mt-[14px] max-w-[420px] text-[14px] text-muted">{desc}</p>
      <div className="mt-[26px]">
        <Button asChild>
          <Link href={href}>{cta}</Link>
        </Button>
      </div>
    </div>
  );
}

export function Forbidden() {
  return (
    <SysScreen
      code="403"
      title="Нет доступа"
      desc="Этот раздел доступен только администраторам. Обратитесь к владельцу аккаунта для повышения прав."
      danger
    />
  );
}

export function NotFound() {
  return (
    <SysScreen
      code="404"
      title="Страница не найдена"
      desc="Запрашиваемый раздел не существует или был перемещён."
    />
  );
}

export function ServerError() {
  return (
    <SysScreen
      code="500"
      title="Сбой сервера"
      desc="Не удалось обработать запрос. Мы уже разбираемся — попробуйте через минуту."
      danger
    />
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { Manager } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import { Button, DataTable, EmptyState, Skeleton } from "@/components/ui";

export default function ManagersPage() {
  const router = useRouter();
  const admin = useIsAdmin();
  const [managers, setManagers] = useState<Manager[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!admin) return;
    fetch("/api/managers", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setManagers(data as Manager[]);
        setLoaded(true);
      });
  }, [admin]);

  if (admin === false) return <Forbidden />;

  const actions = (
    <Button sm onClick={() => router.push("/admin/managers/new")}>
      + Добавить менеджера
    </Button>
  );

  return (
    <Page title="Менеджеры" kicker="Администрирование" actions={actions}>
      {!loaded ? (
        <div className="border border-border">
          {[0, 1, 2].map((i) => (
            <div key={i} className="border-b border-border px-[18px] py-4">
              <Skeleton h={16} />
            </div>
          ))}
        </div>
      ) : managers.length === 0 ? (
        <EmptyState
          title="Нет менеджеров"
          desc="Добавьте менеджеров, чтобы привязывать к ним записи и отслеживать прогресс."
          cta="Добавить менеджера"
          onCta={() => router.push("/admin/managers/new")}
        />
      ) : (
        <DataTable
          highlightCol={3}
          onRow={(m) => router.push(`/admin/managers/${m.id}`)}
          rows={managers}
          cols={[
            { h: "ФИО", nowrap: true, cell: (m) => m.full_name },
            { h: "Должность", nowrap: true, cell: (m) => <span className="text-muted">{m.position}</span> },
            { h: "Device ID", nowrap: true, cell: (m) => <span className="mono text-[12px] text-muted-2">{m.device_id ?? "—"}</span> },
            {
              h: "Статус",
              nowrap: true,
              cell: (m) => (
                <span
                  className="mono inline-flex items-center gap-[7px] text-[11px]"
                  style={{ color: m.is_active ? "var(--success)" : "var(--muted-2)" }}
                >
                  <span style={{ width: 7, height: 7, background: m.is_active ? "var(--success)" : "var(--muted-2)" }} />
                  {m.is_active ? "Активен" : "Неактивен"}
                </span>
              ),
            },
          ]}
        />
      )}
    </Page>
  );
}

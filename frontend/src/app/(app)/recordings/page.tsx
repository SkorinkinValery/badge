"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { isAdmin } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { LIVE_STATUSES } from "@/lib/pipeline";
import type { Manager, Recording } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { cn } from "@/lib/cn";
import {
  Button,
  DataTable,
  EmptyState,
  PageError,
  Skeleton,
  StatusBadge,
  inputClass,
} from "@/components/ui";

const FILTERS: [string, string][] = [
  ["all", "Все"],
  ["done", "Готово"],
  ["progress", "В работе"],
  ["failed", "Ошибка"],
];

async function loadData() {
  const [recordings, managers] = await Promise.all([
    apiFetch<Recording[]>("/api/recordings"),
    apiFetch<Manager[]>("/api/managers"),
  ]);
  return { recordings, managers };
}

export default function RecordingsPage() {
  const router = useRouter();
  const [admin, setAdmin] = useState(false);
  const [q, setQ] = useState("");
  const [st, setSt] = useState("all");
  const { data, loading, error, reload } = useFetch(loadData, []);

  useEffect(() => setAdmin(isAdmin()), []);

  const actions = admin ? (
    <>
      <Button variant="ghost" sm onClick={() => router.push("/recordings/upload")}>
        ↑ Загрузить
      </Button>
      <Button sm onClick={() => router.push("/recordings/record")}>
        ● Записать
      </Button>
    </>
  ) : (
    <Button sm onClick={() => router.push("/recordings/record")}>
      ● Записать
    </Button>
  );

  const managers = data?.managers ?? [];
  const mgrName = (id: string) => managers.find((m) => m.id === id)?.full_name ?? "—";
  const all = data?.recordings ?? [];
  const rows = all.filter((r) => {
    const stOk =
      st === "all" ||
      (st === "progress" ? LIVE_STATUSES.includes(r.status) || r.status === "queued" : r.status === st);
    const qOk =
      q === "" || mgrName(r.manager_id).toLowerCase().includes(q.toLowerCase()) || r.id.includes(q);
    return stOk && qOk;
  });

  return (
    <Page title="Записи" kicker={`${all.length} звонков`} actions={actions}>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Поиск по менеджеру или ID…"
          className={cn(inputClass, "w-[300px] max-w-full")}
        />
        <div className="flex border border-border-2">
          {FILTERS.map(([k, l], i) => (
            <button
              key={k}
              onClick={() => setSt(k)}
              className={cn(
                "mono px-[14px] py-[9px] text-[11.5px]",
                i > 0 && "border-l border-border-2",
                st === k ? "bg-accent font-bold text-black" : "text-muted",
              )}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="border border-border">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="border-b border-border px-[18px] py-[15px]">
              <Skeleton h={16} />
            </div>
          ))}
        </div>
      )}
      {error && <PageError code="LIST_FETCH_FAILED" onRetry={reload} msg={error} />}
      {!loading && !error && all.length === 0 && (
        <EmptyState
          title="Записей пока нет"
          desc="Загрузите аудиофайл или запишите звонок — анализ начнётся автоматически."
          cta="Записать звонок"
          onCta={() => router.push("/recordings/record")}
        />
      )}
      {!loading && !error && all.length > 0 && rows.length === 0 && (
        <EmptyState
          title="Ничего не найдено"
          desc="Измените запрос или сбросьте фильтры."
          cta="Сбросить"
          onCta={() => {
            setQ("");
            setSt("all");
          }}
        />
      )}
      {!loading && !error && rows.length > 0 && (
        <DataTable
          highlightCol={4}
          onRow={(r) => router.push(`/recordings/${r.id}`)}
          rows={rows}
          cols={[
            { h: "ID", nowrap: true, cell: (r) => <span className="mono text-[12px] text-muted">{r.id.slice(0, 8)}</span> },
            { h: "Менеджер", nowrap: true, cell: (r) => mgrName(r.manager_id) },
            { h: "Канал", nowrap: true, cell: (r) => <span className="mono text-[12px]">{r.channel}</span> },
            { h: "Дата", nowrap: true, cell: (r) => <span className="mono text-[12px] text-muted">{r.created_at.replace("T", " ").slice(0, 16)}</span> },
            { h: "Статус", nowrap: true, cell: (r) => <StatusBadge status={r.status} /> },
          ]}
        />
      )}
    </Page>
  );
}

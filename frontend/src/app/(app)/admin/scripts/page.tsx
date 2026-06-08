"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { Script } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import { Button, DataTable, EmptyState, Field, Modal, PixelH, Skeleton, inputClass, toast } from "@/components/ui";

export default function ScriptsPage() {
  const router = useRouter();
  const admin = useIsAdmin();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  function loadScripts() {
    fetch("/api/scripts", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setScripts(data as Script[]);
        setLoaded(true);
      });
  }

  useEffect(() => {
    if (admin) loadScripts();
  }, [admin]);

  if (admin === false) return <Forbidden />;

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file || !newName) return;
    const form = new FormData();
    form.append("name", newName);
    form.append("file", file);
    await fetch("/api/scripts", { method: "POST", headers: authHeaders() as Record<string, string>, body: form });
    setModalOpen(false);
    setNewName("");
    toast("Скрипт загружен", "success");
    loadScripts();
  }

  const actions = (
    <Button sm onClick={() => setModalOpen(true)}>
      + Новый скрипт
    </Button>
  );

  return (
    <Page title="Скрипты" kicker="Администрирование" actions={actions}>
      {!loaded ? (
        <div className="border border-border">
          {[0, 1, 2].map((i) => (
            <div key={i} className="border-b border-border px-[18px] py-4">
              <Skeleton h={16} />
            </div>
          ))}
        </div>
      ) : scripts.length === 0 ? (
        <EmptyState
          title="Нет скриптов"
          desc="Создайте скрипт продаж с набором KPI — по нему будут оцениваться звонки."
          cta="Новый скрипт"
          onCta={() => setModalOpen(true)}
        />
      ) : (
        <DataTable
          highlightCol={1}
          onRow={(s) => router.push(`/admin/scripts/${s.id}`)}
          rows={scripts}
          cols={[
            { h: "Название", nowrap: true, cell: (s) => <span className="font-medium">{s.name}</span> },
            {
              h: "Версия",
              nowrap: true,
              cell: (s) =>
                s.active_version_id ? (
                  <span className="mono text-[12px] text-accent">Активная версия</span>
                ) : (
                  <span className="text-[12px] text-muted-2">Нет</span>
                ),
            },
            {
              h: "Статус",
              nowrap: true,
              cell: (s) => (
                <span
                  className="mono inline-flex items-center gap-[7px] text-[11px]"
                  style={{ color: s.is_active ? "var(--success)" : "var(--muted-2)" }}
                >
                  <span style={{ width: 7, height: 7, background: s.is_active ? "var(--success)" : "var(--muted-2)" }} />
                  {s.is_active ? "Активен" : "Архив"}
                </span>
              ),
            },
          ]}
        />
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Загрузить скрипт" w={440}>
        <div className="flex flex-col gap-4 p-6">
          <PixelH size={22}>Загрузить скрипт</PixelH>
          <Field label="Название скрипта">
            <input className={inputClass} value={newName} onChange={(e) => setNewName(e.target.value)} />
          </Field>
          <input ref={fileRef} type="file" accept=".txt,.md" className="mono text-[12px] text-muted" />
          <div className="flex justify-end gap-[10px]">
            <Button variant="ghost" sm onClick={() => setModalOpen(false)}>
              Отмена
            </Button>
            <Button sm onClick={handleUpload}>
              Загрузить
            </Button>
          </div>
        </div>
      </Modal>
    </Page>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { Manager, Recording, Script } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import {
  Button,
  ConfirmDialog,
  DataTable,
  Field,
  Panel,
  Skeleton,
  StatusBadge,
  inputClass,
  toast,
} from "@/components/ui";

async function getJson<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url, { headers: authHeaders() });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

export default function ManagerDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;
  const admin = useIsAdmin();

  const [manager, setManager] = useState<Manager | null>(null);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [del, setDel] = useState(false);

  // editable fields
  const [fullName, setFullName] = useState("");
  const [position, setPosition] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [scriptId, setScriptId] = useState("");
  const [active, setActive] = useState(true);

  useEffect(() => {
    if (!admin) return;
    Promise.all([
      getJson<Manager>(`/api/managers/${id}`),
      getJson<Script[]>(`/api/scripts`),
      getJson<Recording[]>(`/api/recordings?manager_id=${id}`),
    ]).then(([m, s, recs]) => {
      if (m) {
        setManager(m);
        setFullName(m.full_name);
        setPosition(m.position);
        setDeviceId(m.device_id ?? "");
        setScriptId(m.default_script_id ?? "");
        setActive(m.is_active);
      }
      setScripts(Array.isArray(s) ? s : []);
      setRecordings(Array.isArray(recs) ? recs : []);
      setLoaded(true);
    });
  }, [admin, id]);

  if (admin === false) return <Forbidden />;

  const crumb = [{ label: "Менеджеры", href: "/admin/managers" }, { label: manager?.full_name ?? id?.slice(0, 8) }];

  if (!loaded) {
    return (
      <Page wide crumb={crumb} title="Загрузка…">
        <Skeleton h={300} />
      </Page>
    );
  }
  if (!manager) {
    return (
      <Page wide crumb={crumb} title="Менеджер не найден">
        <p className="text-muted">Запрашиваемый менеджер не существует.</p>
      </Page>
    );
  }

  async function save() {
    const resp = await fetch(`/api/managers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        full_name: fullName.trim(),
        position: position.trim(),
        device_id: deviceId.trim() || null,
        default_script_id: scriptId || null,
        is_active: active,
      }),
    });
    if (resp.ok) toast("Изменения сохранены", "success");
    else {
      const b = await resp.json().catch(() => ({}));
      toast(b?.detail ?? "Ошибка сохранения", "error");
    }
  }

  async function deactivate() {
    await fetch(`/api/managers/${id}`, { method: "DELETE", headers: authHeaders() });
    toast("Менеджер деактивирован", "success");
    router.push("/admin/managers");
  }

  return (
    <Page
      wide
      crumb={crumb}
      title={manager.full_name}
      kicker={manager.position}
      actions={
        <>
          <Button variant="danger" sm onClick={() => setDel(true)}>
            Деактивировать
          </Button>
          <Button sm onClick={save}>
            Сохранить
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[360px_1fr]">
        <div className="flex flex-col gap-4 self-start border border-border bg-bg p-6">
          <span className="mono text-[11px] uppercase tracking-[.08em] text-muted">Карточка менеджера</span>
          <Field label="ФИО">
            <input className={inputClass} value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </Field>
          <Field label="Должность">
            <input className={inputClass} value={position} onChange={(e) => setPosition(e.target.value)} />
          </Field>
          <Field label="Device ID">
            <input className={inputClass} value={deviceId} onChange={(e) => setDeviceId(e.target.value)} />
          </Field>
          <Field label="Скрипт по умолчанию">
            <select className={inputClass} value={scriptId} onChange={(e) => setScriptId(e.target.value)}>
              <option value="">Не выбран</option>
              {scripts.filter((s) => s.is_active).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <label className="flex cursor-pointer items-center gap-[10px] text-[13px] text-muted">
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="accent-accent" />
            Активен
          </label>
        </div>

        <Panel title="Последние звонки менеджера" pad={0}>
          {recordings.length === 0 ? (
            <div className="px-5 py-10 text-center text-[13px] text-muted-2">Звонков пока нет</div>
          ) : (
            <DataTable
              onRow={(r) => router.push(`/recordings/${r.id}`)}
              rows={recordings.slice(0, 8)}
              cols={[
                { h: "Дата", nowrap: true, cell: (r) => <span className="mono text-[12px] text-muted">{r.created_at.replace("T", " ").slice(0, 16)}</span> },
                { h: "Канал", nowrap: true, cell: (r) => <span className="mono text-[12px]">{r.channel}</span> },
                { h: "Статус", cell: (r) => <StatusBadge status={r.status} /> },
              ]}
            />
          )}
        </Panel>
      </div>

      <ConfirmDialog
        open={del}
        title="Деактивировать менеджера?"
        body={`Менеджер «${manager.full_name}» будет деактивирован. Записи звонков сохранятся.`}
        confirmText="Деактивировать"
        danger
        onConfirm={deactivate}
        onClose={() => setDel(false)}
      />
    </Page>
  );
}

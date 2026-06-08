"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { Script, ScriptVersion } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import { Button, Panel, Skeleton, toast } from "@/components/ui";
import { cn } from "@/lib/cn";

async function getJson<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url, { headers: authHeaders() });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

export default function ScriptDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const admin = useIsAdmin();
  const fileRef = useRef<HTMLInputElement>(null);

  const [script, setScript] = useState<Script | null>(null);
  const [versions, setVersions] = useState<ScriptVersion[]>([]);
  const [loaded, setLoaded] = useState(false);

  function reload() {
    Promise.all([
      getJson<Script>(`/api/scripts/${id}`),
      getJson<ScriptVersion[]>(`/api/scripts/${id}/versions`),
    ]).then(([s, v]) => {
      setScript(s);
      setVersions(Array.isArray(v) ? v : []);
      setLoaded(true);
    });
  }

  useEffect(() => {
    if (admin) reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [admin, id]);

  if (admin === false) return <Forbidden />;

  const crumb = [{ label: "Скрипты", href: "/admin/scripts" }, { label: script?.name ?? id?.slice(0, 8) }];

  if (!loaded) {
    return (
      <Page wide crumb={crumb} title="Загрузка…">
        <Skeleton h={300} />
      </Page>
    );
  }
  if (!script) {
    return (
      <Page wide crumb={crumb} title="Скрипт не найден">
        <p className="text-muted">Запрашиваемый скрипт не существует.</p>
      </Page>
    );
  }

  async function uploadVersion() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    await fetch(`/api/scripts/${id}/versions`, { method: "POST", headers: authHeaders() as Record<string, string>, body: form });
    toast("Новая версия загружена", "success");
    reload();
  }

  async function setActive(versionId: string) {
    await fetch(`/api/scripts/${id}/active-version`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ version_id: versionId }),
    });
    toast("Активная версия обновлена", "success");
    reload();
  }

  const current = versions.find((v) => v.id === script.active_version_id) ?? versions[versions.length - 1];

  return (
    <Page
      wide
      crumb={crumb}
      title={script.name}
      kicker="Скрипт"
      actions={
        <Button variant="ghost" sm onClick={() => fileRef.current?.click()}>
          + Новая версия
        </Button>
      }
    >
      <input ref={fileRef} type="file" accept=".txt,.md" className="hidden" onChange={uploadVersion} />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_340px]">
        <Panel title="Содержимое активной версии">
          {current ? (
            <pre className="mono max-h-[520px] overflow-auto whitespace-pre-wrap text-[12.5px] text-muted">
              {current.content}
            </pre>
          ) : (
            <div className="py-8 text-center text-[13px] text-muted-2">Версий пока нет</div>
          )}
        </Panel>

        <Panel title="История версий" pad={0}>
          {versions.length === 0 ? (
            <div className="px-5 py-8 text-center text-[13px] text-muted-2">Нет версий</div>
          ) : (
            <div>
              {[...versions]
                .sort((a, b) => b.version - a.version)
                .map((v) => {
                  const isCurrent = v.id === script.active_version_id;
                  return (
                    <div
                      key={v.id}
                      className={cn(
                        "border-b border-border px-[18px] py-4",
                        isCurrent && "border-l-2 border-l-accent bg-accent-soft",
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className="mono text-[13px] font-bold"
                          style={{ color: isCurrent ? "var(--accent)" : "var(--text)" }}
                        >
                          v{v.version}
                          {isCurrent && " · текущая"}
                        </span>
                        {!isCurrent && (
                          <button onClick={() => setActive(v.id)} className="mono text-[11px] text-accent">
                            сделать активной
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </Panel>
      </div>
    </Page>
  );
}

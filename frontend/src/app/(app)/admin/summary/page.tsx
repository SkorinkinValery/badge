"use client";

import { useEffect, useState } from "react";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { DailySummary, Manager } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import { Field, Panel, ScaleBar, StatCallout, inputClass } from "@/components/ui";

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}м ${s}с`;
}

export default function SummaryPage() {
  const admin = useIsAdmin();
  const [managers, setManagers] = useState<Manager[]>([]);
  const [managerId, setManagerId] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!admin) return;
    fetch("/api/managers", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data: Manager[]) => {
        setManagers(data);
        if (data.length > 0) setManagerId(data[0].id);
        setLoaded(true);
      });
  }, [admin]);

  useEffect(() => {
    if (!managerId || !date) return;
    const params = new URLSearchParams({ manager_id: managerId, date });
    fetch(`/api/admin/summary?${params}`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => setSummary(data as DailySummary));
  }, [managerId, date]);

  if (admin === false) return <Forbidden />;
  if (!loaded) return <Page title="Дневная сводка" kicker="Администрирование">{null}</Page>;

  return (
    <Page wide title="Дневная сводка" kicker="Администрирование">
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <div className="w-[260px]">
          <Field label="Менеджер">
            <select className={inputClass} value={managerId} onChange={(e) => setManagerId(e.target.value)}>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="w-[180px]">
          <Field label="Дата">
            <input className={inputClass} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
        </div>
      </div>

      {summary && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-[14px] lg:grid-cols-4">
            <StatCallout label="Звонков" value={summary.total_recordings} sub="за день" />
            <StatCallout label="Общая длит." value={formatDuration(summary.total_duration_s)} />
            <StatCallout label="Ср. длит." value={formatDuration(summary.avg_duration_s)} />
            <StatCallout
              label="Ср. балл"
              value={summary.avg_score !== null ? `${summary.avg_score.toFixed(1)}%` : "—"}
              accent
            />
          </div>

          {summary.total_recordings === 0 && (
            <p className="text-muted">Нет данных за выбранный день.</p>
          )}

          {summary.kpi_stats.length > 0 && (
            <Panel title="Выполнение KPI" className="mb-6">
              <div className="flex flex-col">
                {summary.kpi_stats.map((k) => (
                  <div key={k.kpi_id} className="border-b border-border py-[14px]">
                    <div className="mb-[9px] flex justify-between gap-3">
                      <span className="text-[13.5px]">{k.label}</span>
                      <span className="num text-[15px]">{k.fulfilled_pct.toFixed(0)}%</span>
                    </div>
                    <ScaleBar v={Math.round(k.fulfilled_pct / 10)} max={10} />
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {summary.violations.length > 0 && (
            <Panel title="Нарушения регламента" className="mb-6">
              <div className="flex flex-wrap gap-2">
                {summary.violations.map((v) => (
                  <span key={v} className="mono border border-danger/40 px-[9px] py-1 text-[11px] text-danger">
                    {v}
                  </span>
                ))}
              </div>
            </Panel>
          )}

          {summary.top_issues.length > 0 && (
            <Panel title="Топ проблемных пунктов">
              <ol className="flex flex-col gap-2">
                {summary.top_issues.map((issue, i) => (
                  <li key={i} className="text-[13px] text-muted">
                    {i + 1}. {issue}
                  </li>
                ))}
              </ol>
            </Panel>
          )}
        </>
      )}
    </Page>
  );
}

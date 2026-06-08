"use client";

import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { verdictFromScore, LIVE_STATUSES, type Verdict } from "@/lib/pipeline";
import type { Analysis, KpiItem, KpiValue, Manager, Recording } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import {
  Button,
  DataTable,
  Delta,
  EmptyState,
  KpiBars,
  Legend,
  LBracket,
  PageError,
  Panel,
  Skeleton,
  StatCallout,
  StatusBadge,
  TrendLine,
} from "@/components/ui";

interface DashData {
  recordings: Recording[];
  managers: Manager[];
  kpi: KpiItem[];
  analyses: Record<string, Analysis>;
}

function kpiNum(v: KpiValue | undefined): number | null {
  if (typeof v === "number") return v;
  if (typeof v === "boolean") return v ? 1 : 0;
  if (v && typeof v === "object" && "value" in v) {
    const x = v.value;
    return typeof x === "number" ? x : typeof x === "boolean" ? (x ? 1 : 0) : null;
  }
  return null;
}

async function loadDashboard(): Promise<DashData> {
  const [recordings, managers, kpi] = await Promise.all([
    apiFetch<Recording[]>("/api/recordings"),
    apiFetch<Manager[]>("/api/managers"),
    apiFetch<KpiItem[]>("/api/kpi"),
  ]);
  const done = recordings.filter((r) => r.status === "done");
  const entries = await Promise.all(
    done.map(async (r) => {
      try {
        return [r.id, await apiFetch<Analysis>(`/api/recordings/${r.id}/analysis`)] as const;
      } catch {
        return null;
      }
    }),
  );
  const analyses: Record<string, Analysis> = {};
  for (const e of entries) if (e) analyses[e[0]] = e[1];
  return { recordings, managers, kpi, analyses };
}

export default function DashboardPage() {
  const router = useRouter();
  const { data, loading, error, reload } = useFetch(loadDashboard, []);

  const kicker = "Обзор";
  const actions = (
    <>
      <Button variant="ghost" sm onClick={() => router.push("/admin/summary")}>
        Дневная сводка
      </Button>
      <Button sm onClick={() => router.push("/recordings/record")}>
        ● Записать звонок
      </Button>
    </>
  );

  if (loading) {
    return (
      <Page title="Дашборд" kicker={kicker}>
        <div className="mb-6 grid grid-cols-2 gap-px border border-border md:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="p-6">
              <Skeleton h={40} w="60%" />
              <Skeleton h={12} w="80%" className="mt-[14px]" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <Skeleton h={300} />
          <Skeleton h={300} />
        </div>
      </Page>
    );
  }
  if (error) {
    return (
      <Page title="Дашборд" kicker={kicker}>
        <PageError code="DASH_AGG_FAILED" onRetry={reload} msg={error} />
      </Page>
    );
  }
  if (!data || data.recordings.length === 0) {
    return (
      <Page title="Дашборд" kicker={kicker}>
        <EmptyState
          title="Нет данных за период"
          desc="Пока нет обработанных звонков. Загрузите запись или запишите звонок с микрофона."
          cta="Загрузить запись"
          onCta={() => router.push("/recordings/upload")}
        />
      </Page>
    );
  }

  const { recordings, managers, kpi, analyses } = data;
  const mgrName = (id: string) => managers.find((m) => m.id === id)?.full_name ?? "—";
  const analysisList = Object.values(analyses);
  const scored = analysisList.filter((a) => a.score != null) as (Analysis & { score: number })[];

  const calls = recordings.length;
  const failed = recordings.filter((r) => r.status === "failed").length;
  const inProgress = recordings.filter((r) => LIVE_STATUSES.includes(r.status) || r.status === "queued").length;
  const avgScore = scored.length
    ? Math.round((scored.reduce((s, a) => s + a.score, 0) / scored.length) * 10) / 10
    : 0;
  const passed = scored.filter((a) => (a.verdict ?? verdictFromScore(a.score)) === "+").length;
  const passRate = scored.length ? Math.round((passed / scored.length) * 100) : 0;

  // KPI bars: average of scale baseline KPIs (0..10 → %)
  const scaleKpis = kpi.filter((k) => k.type === "scale" && k.applies_to === "baseline").slice(0, 5);
  const kpiBars = scaleKpis.map((k) => {
    const vals = analysisList
      .map((a) => kpiNum(a.kpi_json?.[k.id]))
      .filter((v): v is number => v != null);
    const avg = vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
    return { label: k.label, v: Math.round((avg / 10) * 100) };
  });

  // Trend: avg score grouped by day
  const byDay = new Map<string, number[]>();
  for (const r of recordings) {
    const a = analyses[r.id];
    if (a?.score == null) continue;
    const day = r.created_at.slice(0, 10);
    (byDay.get(day) ?? byDay.set(day, []).get(day)!).push(a.score);
  }
  const days = Array.from(byDay.keys()).sort().slice(-12);
  const trend = days.map((d) => {
    const arr = byDay.get(d)!;
    return Math.round(arr.reduce((s, v) => s + v, 0) / arr.length);
  });
  const trendLabels = days.map((d) => d.slice(5));

  const recent = [...recordings]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 6);

  return (
    <Page title="Дашборд" kicker={kicker} actions={actions}>
      <LBracket style={{ marginBottom: 26, padding: 0 }}>
        <div className="grid grid-cols-2 md:grid-cols-4">
          {[
            { v: calls, l: "Звонков всего", dl: null },
            { v: avgScore, l: "Средний балл", dl: null },
            { v: `${passRate}%`, l: "Прошли проверку", dl: null },
            { v: failed + inProgress, l: "Требуют внимания", dl: null },
          ].map((s, i) => (
            <div key={i} className={i ? "border-l border-border p-[26px]" : "p-[26px]"}>
              <div className="num" style={{ fontSize: 40, lineHeight: 0.82 }}>
                {s.v}
              </div>
              <div className="mt-[10px] flex flex-wrap items-center gap-2">
                <span className="mono text-[11px] text-muted">{s.l}</span>
                {s.dl != null && <Delta v={s.dl} />}
              </div>
            </div>
          ))}
        </div>
      </LBracket>

      <div className="mb-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Panel title="Выполнение KPI по этапам">
          {kpiBars.length ? <KpiBars data={kpiBars} /> : <Empty />}
        </Panel>
        <Panel title="Динамика среднего балла" right={<StatusBadge status="done" />}>
          {trend.length ? (
            <>
              <TrendLine data={trend} labels={trendLabels} />
              <div className="mt-[14px] flex flex-wrap items-center justify-between gap-3">
                <Legend
                  items={[
                    { c: "var(--accent)", l: "Средний балл" },
                    { c: "var(--accent-2)", l: "Цель 70" },
                  ]}
                />
                <StatCallout label="сейчас" value={avgScore} />
              </div>
            </>
          ) : (
            <Empty />
          )}
        </Panel>
      </div>

      <Panel
        title="Последние звонки"
        pad={0}
        right={
          <button onClick={() => router.push("/recordings")} className="mono text-[11px] text-accent">
            Все записи →
          </button>
        }
      >
        <DataTable
          highlightCol={3}
          onRow={(r) => router.push(`/recordings/${r.id}`)}
          rows={recent}
          cols={[
            { h: "Менеджер", nowrap: true, cell: (r) => mgrName(r.manager_id) },
            { h: "Дата", nowrap: true, cell: (r) => <span className="mono text-[12px] text-muted">{r.created_at.replace("T", " ").slice(0, 16)}</span> },
            { h: "Статус", nowrap: true, cell: (r) => <StatusBadge status={r.status} /> },
            {
              h: "Балл",
              align: "right",
              nowrap: true,
              cell: (r) => {
                const sc = analyses[r.id]?.score;
                return sc != null ? (
                  <span className="num" style={{ fontSize: 18 }}>{sc}</span>
                ) : (
                  <span className="text-muted-2">—</span>
                );
              },
            },
            {
              h: "Вердикт",
              align: "center",
              cell: (r) => {
                const a = analyses[r.id];
                if (a?.score == null) return <span className="text-muted-2">—</span>;
                const v: Verdict = a.verdict ?? verdictFromScore(a.score);
                const c = v === "+" ? "var(--success)" : v === "~" ? "var(--neutral)" : "var(--danger)";
                return <span className="disp" style={{ fontSize: 22, color: c }}>{v}</span>;
              },
            },
          ]}
        />
      </Panel>
    </Page>
  );
}

function Empty() {
  return <div className="py-10 text-center text-[13px] text-muted-2">Недостаточно данных</div>;
}

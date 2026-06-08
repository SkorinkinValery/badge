"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { authHeaders, isAdmin } from "@/lib/auth";
import { verdictFromScore, type Verdict } from "@/lib/pipeline";
import type { Analysis, KpiItem, KpiValue, Recording, Transcript } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import ScoreCorrectionForm from "@/components/ScoreCorrectionForm";
import {
  Button,
  Modal,
  Panel,
  PipelineStepper,
  ScaleBar,
  Skeleton,
  VerdictToken,
  toast,
} from "@/components/ui";

async function fetchOk<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url, { headers: authHeaders() });
    if (!r.ok) return null;
    return (await r.json()) as T;
  } catch {
    return null;
  }
}

function kpiValue(entry: KpiValue): number {
  if (typeof entry === "number") return entry;
  if (typeof entry === "boolean") return entry ? 10 : 0;
  if (entry && typeof entry === "object" && "value" in entry) {
    const v = entry.value;
    return typeof v === "number" ? v : v ? 10 : 0;
  }
  return 0;
}

export default function RecordingCard() {
  const params = useParams();
  const id = params?.id as string;

  const [recording, setRecording] = useState<Recording | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [kpiMeta, setKpiMeta] = useState<KpiItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [admin, setAdmin] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => setAdmin(isAdmin()), []);

  useEffect(() => {
    setLoaded(false);
    Promise.all([
      fetchOk<Recording>(`/api/recordings/${id}`),
      fetchOk<Transcript>(`/api/recordings/${id}/transcript`),
      fetchOk<Analysis>(`/api/recordings/${id}/analysis`),
      fetchOk<KpiItem[]>(`/api/kpi`),
    ]).then(([rec, t, a, k]) => {
      setRecording(rec);
      setTranscript(t && Array.isArray(t.segments) ? t : null);
      setAnalysis(a && a.kpi_json ? a : null);
      setKpiMeta(Array.isArray(k) ? k : []);
      setLoaded(true);
    });
  }, [id, reloadKey]);

  const reanalyze = useCallback(async () => {
    await fetch(`/api/recordings/${id}/process`, { method: "POST", headers: authHeaders() });
    toast("Звонок отправлен на повторный анализ", "info");
  }, [id]);

  const crumb = [{ label: "Записи", href: "/recordings" }, { label: id?.slice(0, 8) }];

  if (!loaded) {
    return (
      <Page wide crumb={crumb} title="Загрузка…">
        <Skeleton h={110} className="mb-5" />
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.45fr_1fr]">
          <Skeleton h={420} />
          <Skeleton h={420} />
        </div>
      </Page>
    );
  }

  if (!recording) {
    return (
      <Page wide crumb={crumb} title="Запись не найдена">
        <p className="text-muted">Запрашиваемая запись не существует или была удалена.</p>
      </Page>
    );
  }

  const metaById = new Map(kpiMeta.map((m) => [m.id, m]));
  const kpiEntries: [string, KpiValue][] = analysis
    ? kpiMeta.length > 0
      ? kpiMeta
          .filter((m) => analysis.kpi_json != null && m.id in analysis.kpi_json)
          .map((m) => [m.id, analysis.kpi_json![m.id]] as [string, KpiValue])
      : Object.entries(analysis.kpi_json ?? {})
    : [];

  const score = analysis?.score ?? null;
  const verdict: Verdict | null =
    analysis == null ? null : analysis.verdict ?? (score != null ? verdictFromScore(score) : null);

  const failed = recording.status === "failed";
  const dur = recording.duration_seconds
    ? `${Math.floor(recording.duration_seconds / 60)}:${String(Math.round(recording.duration_seconds % 60)).padStart(2, "0")}`
    : "—";

  return (
    <Page
      wide
      crumb={crumb}
      title="Разбор звонка"
      kicker={recording.channel === "mic" ? "С микрофона" : "Загруженный файл"}
      actions={
        admin ? (
          <Button variant="ghost" sm onClick={reanalyze}>
            ↻ Переанализировать
          </Button>
        ) : null
      }
    >
      {/* pipeline */}
      <div className="mb-[22px] border border-border bg-bg px-[22px] py-5">
        <div className="mb-7 flex flex-wrap justify-between gap-2">
          <span className="mono text-[11px] uppercase tracking-[.08em] text-muted">
            Конвейер обработки
          </span>
          <span className="mono text-[11px] text-muted">
            длит. {dur} · {recording.created_at.replace("T", " ").slice(0, 16)}
          </span>
        </div>
        <PipelineStepper status={recording.status} failed={failed} />
        {failed && recording.stage_error && (
          <div className="mono mt-4 border-l-2 border-danger pl-3 text-[12px] text-danger">
            {recording.stage_error}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.45fr_1fr]">
        {/* transcript */}
        <Panel
          title="Транскрипт"
          pad={0}
          right={
            transcript?.detected_language ? (
              <span className="mono text-[10.5px] text-muted-2">
                язык · {transcript.detected_language}
              </span>
            ) : undefined
          }
        >
          {transcript && transcript.segments && transcript.segments.length > 0 ? (
            <div className="max-h-[560px] overflow-y-auto py-2">
              {transcript.segments.map((seg, i) => (
                <div key={i} className="flex gap-[14px] px-5 py-[11px]">
                  <span className="mono w-[44px] flex-none pt-[2px] text-[11px] text-muted-2">
                    {Math.floor(seg.start / 60)}:{String(Math.floor(seg.start % 60)).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 text-[13.5px]">{seg.text}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-5 py-10 text-center text-[13px] text-muted-2">
              Транскрипт недоступен — текст разговора ещё не сформирован.
            </div>
          )}
        </Panel>

        {/* score + KPI */}
        <div className="flex flex-col gap-5">
          <div className="border border-border bg-bg px-[22px] py-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="mono mb-[10px] text-[10.5px] uppercase tracking-[.1em] text-muted">
                  Итоговый балл
                </div>
                <div className="flex items-end gap-3">
                  <span className="num" style={{ fontSize: 64, lineHeight: 0.8 }}>
                    {score ?? "—"}
                  </span>
                  <span className="num text-muted-2" style={{ fontSize: 22, paddingBottom: 7 }}>
                    /100
                  </span>
                </div>
              </div>
              {verdict && <VerdictToken verdict={verdict} size={56} />}
            </div>
            {verdict && (
              <div
                className="mono mt-4 text-[12px] tracking-[.08em]"
                style={{
                  color:
                    verdict === "+"
                      ? "var(--success)"
                      : verdict === "~"
                        ? "var(--neutral)"
                        : "var(--danger)",
                }}
              >
                {verdict === "+" ? "СООТВЕТСТВУЕТ" : verdict === "~" ? "ЧАСТИЧНО" : "НЕ СООТВЕТСТВУЕТ"}
              </div>
            )}
            {analysis?.summary && (
              <p className="mt-4 border-t border-border pt-4 text-[13px] text-muted">
                {analysis.summary}
              </p>
            )}
            {admin && analysis && (
              <div className="mt-[18px] border-t border-border pt-4">
                <Button variant="ghost" sm full onClick={() => setCorrecting(true)}>
                  ✎ Скорректировать оценку
                </Button>
              </div>
            )}
          </div>

          {analysis ? (
            <Panel
              title="Чек-лист KPI"
              right={
                <span className="mono text-[10px] text-muted-2">
                  режим · {analysis.mode === "script" ? "скрипт" : "база"}
                </span>
              }
            >
              <div className="flex flex-col">
                {kpiEntries.map(([key, entry]) => {
                  const meta = metaById.get(key);
                  const val = kpiValue(entry);
                  const isFact = meta?.type === "fact";
                  const e = entry && typeof entry === "object" ? entry : null;
                  return (
                    <div key={key} className="border-b border-border py-[14px]">
                      <div className="mb-[9px] flex justify-between gap-3">
                        <span className="text-[13.5px]">{meta?.label ?? key}</span>
                        {isFact ? (
                          <span
                            className="mono text-[13px] font-bold"
                            style={{ color: val >= 10 ? "var(--success)" : "var(--danger)" }}
                          >
                            {val >= 10 ? "✓ ДА" : "✗ НЕТ"}
                          </span>
                        ) : (
                          <span className="mono text-[10.5px] text-muted-2">
                            вес ×{meta?.weight ?? 1}
                          </span>
                        )}
                      </div>
                      {!isFact && <ScaleBar v={val} max={10} />}
                      {e?.quote && (
                        <div className="mono mt-2 border-l-2 border-accent pl-2 text-[11.5px] text-muted">
                          {e.quote}
                        </div>
                      )}
                      {e?.comment && (
                        <div className="mt-1 text-[12px] text-muted-2">{e.comment}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </Panel>
          ) : (
            !failed && (
              <Panel title="Чек-лист KPI">
                <div className="py-6 text-center text-[13px] text-muted-2">
                  Анализ ещё не готов — KPI появятся после обработки.
                </div>
              </Panel>
            )
          )}
        </div>
      </div>

      <Modal open={correcting} onClose={() => setCorrecting(false)} title="Коррекция оценки" w={420}>
        <div className="p-6">
          <h2 className="disp mb-3 text-[22px]">Коррекция оценки</h2>
          {analysis && (
            <ScoreCorrectionForm
              recordingId={id}
              currentScore={analysis.score}
              autoScore={analysis.auto_score}
              currentVerdict={analysis.verdict}
              onSaved={() => {
                setCorrecting(false);
                toast("Оценка обновлена", "success");
                setReloadKey((k) => k + 1);
              }}
            />
          )}
        </div>
      </Modal>
    </Page>
  );
}

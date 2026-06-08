"use client";

import { CSSProperties, ReactNode, useEffect, useState } from "react";
import { PIPELINE, STATUS_INDEX, STATUS_META, LIVE_STATUSES, type Verdict } from "@/lib/pipeline";
import { Button, PixelH, HexMotif, Delta } from "./primitives";

/* ---------- StatCallout: white box + orange label tab ---------- */
export function StatCallout({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="flex min-w-0 flex-col">
      <div className="mono self-start bg-accent px-[9px] py-1 text-[10px] font-bold uppercase tracking-[.12em] text-black">
        {label}
      </div>
      <div
        className="flex flex-1 flex-col justify-center gap-1 px-[18px] pb-[14px] pt-4 text-black"
        style={{ background: accent ? "var(--accent)" : "#fff" }}
      >
        <div className="num text-black" style={{ fontSize: 34, lineHeight: 0.85 }}>
          {value}
        </div>
        {sub && <div className="mono text-[11px] text-[#444]">{sub}</div>}
      </div>
    </div>
  );
}

/* ---------- L-bracket framed stat ---------- */
export function LBracket({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  const c: CSSProperties = {
    position: "absolute",
    width: 16,
    height: 16,
    borderColor: "var(--accent)",
    borderStyle: "solid",
  };
  return (
    <div style={{ position: "relative", padding: "22px", background: "var(--bg)", ...style }}>
      <span style={{ ...c, top: 0, left: 0, borderWidth: "2px 0 0 2px" }} />
      <span style={{ ...c, top: 0, right: 0, borderWidth: "2px 2px 0 0" }} />
      <span style={{ ...c, bottom: 0, left: 0, borderWidth: "0 0 2px 2px" }} />
      <span style={{ ...c, bottom: 0, right: 0, borderWidth: "0 2px 2px 0" }} />
      {children}
    </div>
  );
}

export function LStat({
  value,
  label,
  delta,
}: {
  value: ReactNode;
  label: string;
  delta?: number | null;
}) {
  return (
    <div>
      <div className="num" style={{ fontSize: 38, lineHeight: 0.85 }}>
        {value}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span className="mono text-[11.5px] text-muted">{label}</span>
        {delta != null && <Delta v={delta} />}
      </div>
    </div>
  );
}

/* ---------- Status badge (9 pipeline statuses) ---------- */
export function StatusBadge({ status }: { status: string }) {
  const m = STATUS_META[status] || STATUS_META.uploaded;
  const live = LIVE_STATUSES.includes(status);
  const borderColor =
    status === "failed"
      ? "rgba(239,68,68,.35)"
      : status === "done"
        ? "rgba(34,197,94,.3)"
        : "var(--border-2)";
  return (
    <span
      className="mono inline-flex items-center gap-[7px] border px-[9px] py-1 text-[11px] tracking-[.04em] whitespace-nowrap"
      style={{ color: m.c, borderColor }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          background: m.c,
          flex: "none",
          animation: live ? "pulse 1.1s infinite" : "none",
        }}
      />
      {m.ru.toUpperCase()}
    </span>
  );
}

/* ---------- Verdict token ---------- */
const VERDICT_MAP: Record<Verdict, { c: string; l: string }> = {
  "+": { c: "var(--success)", l: "СООТВЕТСТВУЕТ" },
  "~": { c: "var(--neutral)", l: "ЧАСТИЧНО" },
  "-": { c: "var(--danger)", l: "НЕ СООТВЕТСТВУЕТ" },
};

export function VerdictToken({
  verdict,
  size = 64,
  withLabel,
}: {
  verdict: Verdict;
  size?: number;
  withLabel?: boolean;
}) {
  const m = VERDICT_MAP[verdict] || VERDICT_MAP["~"];
  return (
    <div className="inline-flex items-center gap-4">
      <div
        className="disp text-center"
        style={{ fontSize: size, color: m.c, lineHeight: 0.7, width: size * 0.7 }}
      >
        {verdict}
      </div>
      {withLabel && (
        <div className="mono text-[12px] tracking-[.08em]" style={{ color: m.c }}>
          {m.l}
        </div>
      )}
    </div>
  );
}

/* ---------- KPI checklist ---------- */
export function ScaleBar({
  v,
  max = 10,
  compare,
}: {
  v: number;
  max?: number;
  compare?: number | null;
}) {
  return (
    <div className="flex items-center gap-[10px]">
      <div className="relative h-2 flex-1 bg-surface-2">
        {compare != null && (
          <div
            className="absolute bg-muted-2"
            style={{ top: -3, bottom: -3, left: `${(compare / max) * 100}%`, width: 2 }}
          />
        )}
        <div className="h-full bg-accent" style={{ width: `${(v / max) * 100}%` }} />
      </div>
      <span className="num text-right text-[18px]" style={{ width: 42 }}>
        {v}
        <span className="text-[12px] text-muted-2">/{max}</span>
      </span>
    </div>
  );
}

export interface ScaleKpi {
  id: string;
  name: string;
  baseline: number;
  script: number;
  [k: string]: string | number;
}
export interface FactKpi {
  id: string;
  name: string;
  baseline: boolean;
  script: boolean;
  [k: string]: string | boolean;
}

export function KpiChecklist({
  scale,
  fact,
  column = "script",
}: {
  scale: ScaleKpi[];
  fact: FactKpi[];
  column?: string;
}) {
  return (
    <div className="flex flex-col">
      {scale.map((k) => (
        <div key={k.id} className="border-b border-border py-[14px]">
          <div className="mb-[9px] flex justify-between gap-3">
            <span className="text-[13.5px]">{k.name}</span>
            <span className="mono text-[10.5px] text-muted-2">база {k.baseline}/10</span>
          </div>
          <ScaleBar v={k[column] as number} compare={k.baseline} />
        </div>
      ))}
      {fact.map((k) => {
        const ok = k[column] as boolean;
        return (
          <div
            key={k.id}
            className="flex items-center justify-between gap-3 border-b border-border py-[13px]"
          >
            <span className="text-[13.5px]">{k.name}</span>
            <span
              className="mono text-[13px] font-bold"
              style={{ color: ok ? "var(--success)" : "var(--danger)" }}
            >
              {ok ? "✓ ДА" : "✗ НЕТ"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- Pipeline stepper (diamond nodes) ---------- */
export function PipelineStepper({ status, failed }: { status: string; failed?: boolean }) {
  const cur = STATUS_INDEX[status === "failed" ? "analyzing" : status] ?? 0;
  const failAt = failed ? cur : -1;
  return (
    <div className="flex items-start overflow-x-auto pb-[6px]">
      {PIPELINE.map((s, i) => {
        const done = i < cur;
        const active = i === cur && !failed;
        const isFail = failed && i === failAt;
        const col = isFail
          ? "var(--danger)"
          : done
            ? "var(--success)"
            : active
              ? "var(--accent)"
              : "var(--border-2)";
        const last = i === PIPELINE.length - 1;
        return (
          <div
            key={s.key}
            className="flex items-start"
            style={{ flex: last ? "none" : 1, minWidth: last ? "auto" : 64 }}
          >
            <div className="flex flex-none flex-col items-center gap-2">
              <div
                style={{
                  width: 18,
                  height: 18,
                  transform: "rotate(45deg)",
                  background: done || active || isFail ? col : "transparent",
                  border: "2px solid " + col,
                  boxShadow: active ? "0 0 0 4px var(--accent-soft)" : "none",
                }}
              />
              <span
                className="mono text-center text-[9.5px] tracking-[.04em] whitespace-nowrap"
                style={{ color: active || isFail ? col : "var(--muted-2)", maxWidth: 62 }}
              >
                {s.ru}
              </span>
            </div>
            {!last && (
              <div
                className="mt-2 h-[2px] flex-1"
                style={{ borderTop: "2px dashed " + (i < cur ? "var(--success)" : "var(--border-2)") }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ---------- DataTable (benchmark style) ---------- */
export interface Column<T> {
  h: string;
  k?: keyof T;
  align?: "left" | "right" | "center";
  nowrap?: boolean;
  cell?: (row: T) => ReactNode;
}

export function DataTable<T>({
  cols,
  rows,
  onRow,
  highlightCol,
}: {
  cols: Column<T>[];
  rows: T[];
  onRow?: (row: T) => void;
  highlightCol?: number;
}) {
  return (
    <div className="overflow-x-auto border border-border">
      <table className="w-full border-collapse" style={{ minWidth: 640 }}>
        <thead>
          <tr>
            {cols.map((c, i) => (
              <th
                key={i}
                className="mono border-b border-border px-[18px] py-[15px] text-[11px] font-medium uppercase tracking-[.06em] whitespace-nowrap"
                style={{
                  textAlign: c.align || "left",
                  color: i === highlightCol ? "var(--accent)" : "var(--muted)",
                  background: i === highlightCol ? "rgba(255,90,31,.05)" : "transparent",
                }}
              >
                {c.h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr
              key={ri}
              onClick={onRow ? () => onRow(r) : undefined}
              className={onRow ? "cursor-pointer transition-colors hover:bg-surface" : undefined}
            >
              {cols.map((c, ci) => (
                <td
                  key={ci}
                  className="px-[18px] py-[14px] text-[13.5px] text-text"
                  style={{
                    textAlign: c.align || "left",
                    borderBottom: ri < rows.length - 1 ? "1px solid var(--border)" : "none",
                    background: ci === highlightCol ? "rgba(255,90,31,.05)" : "transparent",
                    whiteSpace: c.nowrap ? "nowrap" : "normal",
                  }}
                >
                  {c.cell ? c.cell(r) : (r[c.k as keyof T] as ReactNode)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- Waveform (mic recording animation) ---------- */
export function Waveform({ active }: { active: boolean }) {
  const [bars, setBars] = useState<number[]>(() => Array.from({ length: 48 }, () => 0.2));
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setBars((b) => b.map(() => 0.15 + Math.random() * 0.85)), 120);
    return () => clearInterval(id);
  }, [active]);
  return (
    <div className="flex h-20 items-center justify-center gap-[3px]">
      {bars.map((h, i) => (
        <div
          key={i}
          style={{
            width: 4,
            height: `${(active ? h : 0.12) * 80}%`,
            minHeight: 3,
            background: active ? "var(--accent)" : "var(--border-2)",
            transition: "height .12s",
          }}
        />
      ))}
    </div>
  );
}

/* ---------- Checkerboard transition ---------- */
export function Checker({ h = 26, flip, color = "#fff" }: { h?: number; flip?: boolean; color?: string }) {
  const sz = h / 2;
  return (
    <div
      style={{
        height: h,
        width: "100%",
        backgroundImage: `linear-gradient(45deg,${color} 25%,transparent 25%,transparent 75%,${color} 75%),linear-gradient(45deg,${color} 25%,transparent 25%,transparent 75%,${color} 75%)`,
        backgroundSize: `${sz}px ${sz}px`,
        backgroundPosition: `0 0,${sz / 2}px ${sz / 2}px`,
        transform: flip ? "scaleY(-1)" : "none",
      }}
    />
  );
}

/* ---------- States: empty + error ---------- */
export function EmptyState({
  title,
  desc,
  cta,
  onCta,
}: {
  title: string;
  desc?: string;
  cta?: string;
  onCta?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center border border-border bg-bg px-6 py-[70px] text-center">
      <HexMotif size={110} />
      <PixelH size={26} className="mt-6">
        {title}
      </PixelH>
      {desc && <p className="mt-3 max-w-[380px] text-[13.5px] text-muted">{desc}</p>}
      {cta && (
        <div className="mt-[22px]">
          <Button onClick={onCta}>{cta}</Button>
        </div>
      )}
    </div>
  );
}

export function PageError({
  onRetry,
  code = "REQUEST_FAILED",
  msg,
}: {
  onRetry?: () => void;
  code?: string;
  msg?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center bg-bg px-6 py-[70px] text-center"
      style={{ border: "1px solid rgba(239,68,68,.3)" }}
    >
      <div className="disp text-danger" style={{ fontSize: 56 }}>
        !
      </div>
      <PixelH size={26} className="mt-[14px]">
        Что-то пошло не так
      </PixelH>
      <p className="mt-3 max-w-[420px] text-[13.5px] text-muted">
        {msg || "Не удалось загрузить данные. Попробуйте обновить страницу."}
      </p>
      <code className="mono mt-[10px] text-[11px] tracking-[.04em] text-danger">ERR · {code}</code>
      {onRetry && (
        <div className="mt-[22px]">
          <Button variant="ghost" onClick={onRetry}>
            ↻ Повторить
          </Button>
        </div>
      )}
    </div>
  );
}

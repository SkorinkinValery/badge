// Recording pipeline stages + status/verdict helpers (ported from design/data.jsx).

export interface PipelineStep {
  key: string;
  ru: string;
  short: string;
}

export const PIPELINE: PipelineStep[] = [
  { key: "uploaded", ru: "Загружено", short: "UPL" },
  { key: "queued", ru: "В очереди", short: "QUE" },
  { key: "normalizing", ru: "Нормализация", short: "NRM" },
  { key: "transcribing", ru: "Транскрипция", short: "TRN" },
  { key: "analyzing", ru: "Анализ", short: "ANL" },
  { key: "scoring", ru: "Оценка", short: "SCR" },
  { key: "exporting", ru: "Экспорт в CRM", short: "EXP" },
  { key: "done", ru: "Готово", short: "OK" },
];

export const STATUS_INDEX: Record<string, number> = Object.fromEntries(
  PIPELINE.map((s, i) => [s.key, i]),
);

export type Verdict = "+" | "~" | "-";

export function verdictFromScore(s: number): Verdict {
  return s >= 80 ? "+" : s >= 55 ? "~" : "-";
}

export interface StatusMeta {
  ru: string;
  c: string;
}

// color is a CSS var token reference
export const STATUS_META: Record<string, StatusMeta> = {
  uploaded: { ru: "Загружено", c: "var(--muted)" },
  queued: { ru: "В очереди", c: "var(--muted)" },
  normalizing: { ru: "Нормализация", c: "var(--accent-2)" },
  transcribing: { ru: "Транскрипция", c: "var(--accent-2)" },
  analyzing: { ru: "Анализ", c: "var(--accent)" },
  scoring: { ru: "Оценка", c: "var(--accent)" },
  exporting: { ru: "Экспорт", c: "var(--accent)" },
  done: { ru: "Готово", c: "var(--success)" },
  failed: { ru: "Ошибка", c: "var(--danger)" },
};

export const LIVE_STATUSES = [
  "normalizing",
  "transcribing",
  "analyzing",
  "scoring",
  "exporting",
];

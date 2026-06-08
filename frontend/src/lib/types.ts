// API response shapes (mirror backend app/api/*).

export interface Recording {
  id: string;
  manager_id: string;
  channel: string;
  status: string;
  consent_flag: boolean;
  created_at: string;
  audio_path: string | null;
  stage_error: string | null;
  retention_until: string | null;
  duration_seconds: number | null;
}

export interface Manager {
  id: string;
  full_name: string;
  position: string;
  device_id: string | null;
  is_active: boolean;
  default_script_id: string | null;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}
export interface Transcript {
  recording_id: string;
  full_text: string | null;
  segments: TranscriptSegment[] | null;
  detected_language: string | null;
}

export type KpiValue = number | boolean | { value?: number | boolean; quote?: string; comment?: string };

export interface Analysis {
  recording_id: string;
  summary: string | null;
  kpi_json: Record<string, KpiValue> | null;
  score: number | null;
  auto_score: number | null;
  verdict: "+" | "~" | "-" | null;
  mode: string;
  weights_version: string | null;
}

export interface KpiItem {
  id: string;
  label: string;
  type: "scale" | "fact";
  weight: number;
  applies_to: "baseline" | "script";
  include_in_score: boolean;
}

export interface Script {
  id: string;
  name: string;
  is_active: boolean;
  active_version_id: string | null;
}
export interface ScriptVersion {
  id: string;
  script_id: string;
  version: number;
  content: string;
  kpi_binding: Record<string, unknown> | null;
}

export interface User {
  id: string;
  login: string;
  role: string;
  is_active: boolean;
}

export interface KpiStat {
  kpi_id: string;
  label: string;
  fulfilled_pct: number;
}
export interface DailySummary {
  manager_id: string;
  date: string;
  total_recordings: number;
  total_duration_s: number;
  avg_duration_s: number;
  avg_score: number | null;
  kpi_stats: KpiStat[];
  violations: string[];
  top_issues: string[];
}

export interface CrmSettings {
  active_crm: string;
  available_providers: string[];
  params: Record<string, string>;
}

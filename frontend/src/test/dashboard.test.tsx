import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderUI } from "./render";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

import DashboardPage from "@/app/(app)/dashboard/page";

const REC = {
  id: "rec-1",
  manager_id: "m-1",
  channel: "file",
  status: "done",
  consent_flag: true,
  created_at: "2026-06-07T14:00:00",
  audio_path: "k",
  stage_error: null,
  retention_until: null,
  duration_seconds: 120,
};
const MANAGER = { id: "m-1", full_name: "Алёна Кравцова", position: "Менеджер", device_id: null, is_active: true, default_script_id: null };
const KPI = [{ id: "greeting", label: "Установление контакта", type: "scale", weight: 1, applies_to: "baseline", include_in_score: true }];
const ANALYSIS = { recording_id: "rec-1", summary: "ok", kpi_json: { greeting: 8 }, score: 82, auto_score: 82, verdict: "+", mode: "baseline", weights_version: "1.0" };

function mockFetch(recordings: unknown[]) {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    const json = url.includes("/analysis")
      ? ANALYSIS
      : url.includes("/api/recordings")
        ? recordings
        : url.includes("/api/managers")
          ? [MANAGER]
          : url.includes("/api/kpi")
            ? KPI
            : {};
    return Promise.resolve({ ok: true, status: 200, json: async () => json });
  });
}

beforeEach(() => {
  mockPush.mockClear();
});

describe("Dashboard", () => {
  it("renders aggregated stats and recent calls", async () => {
    mockFetch([REC]);
    renderUI(<DashboardPage />);
    await waitFor(() => expect(screen.getByText("Дашборд")).toBeInTheDocument());
    // manager name appears in the recent calls table
    await waitFor(() => expect(screen.getByText("Алёна Кравцова")).toBeInTheDocument());
    // total calls stat
    expect(screen.getByText("Звонков всего")).toBeInTheDocument();
  });

  it("shows empty state when there are no recordings", async () => {
    mockFetch([]);
    renderUI(<DashboardPage />);
    await waitFor(() => expect(screen.getByText(/Нет данных за период/i)).toBeInTheDocument());
  });
});

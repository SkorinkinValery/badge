import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { renderUI } from "./render";
import SummaryPage from "@/app/(app)/admin/summary/page";

const mockPush = vi.fn();

vi.mock("@/lib/auth", () => ({
  getToken: () => "admin-token",
  authHeaders: () => ({ Authorization: "Bearer admin-token" }),
  isAdmin: () => true,
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

function wrap(ui: React.ReactElement) {
  return renderUI(ui);
}

const SAMPLE_MANAGERS = [
  { id: "mgr-1", full_name: "Иван Иванов", position: "Менеджер", is_active: true, device_id: null, default_script_id: null },
];

const SAMPLE_SUMMARY = {
  manager_id: "mgr-1",
  date: "2026-06-06",
  total_recordings: 5,
  total_duration_s: 1800.0,
  avg_duration_s: 360.0,
  avg_score: 78.5,
  kpi_stats: [
    { kpi_id: "greeting", label: "Приветствие", kpi_type: "scale", avg_value: 8.0, fulfilled_pct: 80.0 },
    { kpi_id: "cta", label: "CTA", kpi_type: "fact", avg_value: 0.0, fulfilled_pct: 60.0 },
  ],
  violations: ["CTA"],
  top_issues: ["CTA", "Приветствие"],
};

beforeEach(() => {
  mockPush.mockClear();
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes("/api/managers")) {
      return Promise.resolve({ ok: true, json: async () => SAMPLE_MANAGERS });
    }
    if (url.includes("/api/admin/summary")) {
      return Promise.resolve({ ok: true, json: async () => SAMPLE_SUMMARY });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  });
});

describe("Daily summary admin page", () => {
  it("renders page title", async () => {
    wrap(<SummaryPage />);
    await waitFor(() =>
      expect(screen.getByText(/дневная сводка/i)).toBeInTheDocument()
    );
  });

  it("shows manager filter select", async () => {
    wrap(<SummaryPage />);
    await waitFor(() =>
      expect(screen.getByText(/менеджер/i)).toBeInTheDocument()
    );
  });

  it("shows date filter", async () => {
    wrap(<SummaryPage />);
    await waitFor(() =>
      expect(screen.getByLabelText(/дата/i)).toBeInTheDocument()
    );
  });

  it("shows total recordings count when summary loaded", async () => {
    wrap(<SummaryPage />);
    await waitFor(() =>
      expect(screen.getAllByText("5").length).toBeGreaterThan(0)
    );
  });

  it("shows avg score when loaded", async () => {
    wrap(<SummaryPage />);
    await waitFor(() =>
      expect(screen.getByText("78.5%")).toBeInTheDocument()
    );
  });

  it("shows violations list", async () => {
    wrap(<SummaryPage />);
    await waitFor(() =>
      expect(screen.getAllByText("CTA").length).toBeGreaterThan(0)
    );
  });

  it("opens recordings filtered by the selected manager and date", async () => {
    wrap(<SummaryPage />);
    const dateInput = await screen.findByLabelText(/дата/i);
    fireEvent.change(dateInput, { target: { value: "2026-06-06" } });
    const btn = screen.getByRole("button", { name: /открыть записи за день/i });
    fireEvent.click(btn);
    expect(mockPush).toHaveBeenCalledWith("/recordings?manager=mgr-1&date=2026-06-06");
  });
});

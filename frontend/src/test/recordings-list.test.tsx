import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderUI } from "./render";
import RecordingsPage from "@/app/(app)/recordings/page";

vi.mock("@/lib/auth", () => ({
  getToken: () => "test-token",
  authHeaders: () => ({ Authorization: "Bearer test-token" }),
  isAdmin: () => true,
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

const SAMPLE_RECORDINGS = [
  { id: "aaa-111", manager_id: "mgr-1", channel: "file", status: "done", consent_flag: true, created_at: "2026-06-05T12:00:00", audio_path: "/audio/a.wav", stage_error: null, retention_until: null, duration_seconds: 60 },
  { id: "bbb-222", manager_id: "mgr-2", channel: "file", status: "queued", consent_flag: true, created_at: "2026-06-05T13:00:00", audio_path: null, stage_error: null, retention_until: null, duration_seconds: null },
  { id: "ccc-333", manager_id: "mgr-3", channel: "mic", status: "failed", consent_flag: true, created_at: "2026-06-05T14:00:00", audio_path: null, stage_error: "STT error", retention_until: null, duration_seconds: null },
];
const SAMPLE_MANAGERS = [
  { id: "mgr-1", full_name: "Иван Иванов", position: "Менеджер", device_id: null, is_active: true, default_script_id: null },
];

function mockFetch(recordings: unknown[]) {
  global.fetch = vi.fn().mockImplementation((url: string) =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: async () => (url.includes("/api/managers") ? SAMPLE_MANAGERS : recordings),
    }),
  );
}

beforeEach(() => {
  mockPush.mockClear();
  mockFetch(SAMPLE_RECORDINGS);
});

describe("Recordings list page", () => {
  it("renders a table with recordings", async () => {
    renderUI(<RecordingsPage />);
    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
  });

  it("shows status badge for each recording", async () => {
    renderUI(<RecordingsPage />);
    await waitFor(() => expect(screen.getByText("ГОТОВО")).toBeInTheDocument());
    expect(screen.getByText("В ОЧЕРЕДИ")).toBeInTheDocument();
    expect(screen.getByText("ОШИБКА")).toBeInTheDocument();
  });

  it("joins manager names from /api/managers", async () => {
    renderUI(<RecordingsPage />);
    await waitFor(() => expect(screen.getByText("Иван Иванов")).toBeInTheDocument());
  });

  it("shows empty state when no recordings", async () => {
    mockFetch([]);
    renderUI(<RecordingsPage />);
    await waitFor(() => expect(screen.getByText(/Записей пока нет/i)).toBeInTheDocument());
  });
});

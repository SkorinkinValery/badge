import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import RecordingsPage from "@/app/(app)/recordings/page";

vi.mock("@/lib/auth", () => ({
  getToken: () => "test-token",
  authHeaders: () => ({ Authorization: "Bearer test-token" }),
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

function wrap(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

const SAMPLE_RECORDINGS = [
  {
    id: "aaa-111",
    manager_id: "mgr-1",
    channel: "file",
    status: "done",
    consent_flag: true,
    created_at: "2026-06-05T12:00:00Z",
    audio_path: "/audio/a.wav",
    stage_error: null,
    retention_until: null,
  },
  {
    id: "bbb-222",
    manager_id: "mgr-2",
    channel: "file",
    status: "queued",
    consent_flag: true,
    created_at: "2026-06-05T13:00:00Z",
    audio_path: null,
    stage_error: null,
    retention_until: null,
  },
  {
    id: "ccc-333",
    manager_id: "mgr-3",
    channel: "file",
    status: "failed",
    consent_flag: true,
    created_at: "2026-06-05T14:00:00Z",
    audio_path: null,
    stage_error: "STT error",
    retention_until: null,
  },
];

beforeEach(() => {
  mockPush.mockClear();
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => SAMPLE_RECORDINGS,
  });
});

describe("Recordings list page", () => {
  it("renders a table with recordings", async () => {
    wrap(<RecordingsPage />);
    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
  });

  it("shows status for each recording", async () => {
    wrap(<RecordingsPage />);
    await waitFor(() => expect(screen.getByText("done")).toBeInTheDocument());
    expect(screen.getByText("queued")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("shows empty state when no recordings", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    wrap(<RecordingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/нет записей/i)).toBeInTheDocument()
    );
  });
});

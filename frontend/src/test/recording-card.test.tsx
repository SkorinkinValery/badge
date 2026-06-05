import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import RecordingCard from "@/app/recordings/[id]/page";

vi.mock("@/lib/auth", () => ({
  getToken: () => "test-token",
  authHeaders: () => ({ Authorization: "Bearer test-token" }),
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ id: "aaa-111" }),
}));

function wrap(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

const TRANSCRIPT = {
  recording_id: "aaa-111",
  full_text: "Добрый день, чем могу помочь?",
  segments: [
    { start: 0, end: 2, text: "Добрый день," },
    { start: 2, end: 4, text: "чем могу помочь?" },
  ],
  detected_language: "ru",
};

const ANALYSIS = {
  recording_id: "aaa-111",
  summary: "Менеджер хорошо представился.",
  kpi_json: {
    greeting: { value: 8.0, quote: "Добрый день", comment: "хорошо" },
  },
  score: 80.0,
  auto_score: 80.0,
  verdict: "+",
  mode: "baseline",
  weights_version: "v10.0",
};

const RECORDING = {
  id: "aaa-111",
  manager_id: "mgr-1",
  channel: "file",
  status: "done",
  consent_flag: true,
  created_at: "2026-06-05T12:00:00Z",
  audio_path: "/recordings/aaa-111.wav",
  stage_error: null,
  retention_until: null,
};

beforeEach(() => {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes("/transcript")) {
      return Promise.resolve({ ok: true, json: async () => TRANSCRIPT });
    }
    if (url.includes("/analysis")) {
      return Promise.resolve({ ok: true, json: async () => ANALYSIS });
    }
    return Promise.resolve({ ok: true, json: async () => RECORDING });
  });
});

describe("Recording card page", () => {
  it("shows full transcript text", async () => {
    wrap(<RecordingCard />);
    await waitFor(() =>
      expect(screen.getAllByText(/чем могу помочь/).length).toBeGreaterThan(0)
    );
  });

  it("shows summary", async () => {
    wrap(<RecordingCard />);
    await waitFor(() =>
      expect(screen.getByText(/Менеджер хорошо представился/i)).toBeInTheDocument()
    );
  });

  it("shows score and verdict", async () => {
    wrap(<RecordingCard />);
    await waitFor(() => expect(screen.getByText("80")).toBeInTheDocument());
    expect(screen.getByText("+")).toBeInTheDocument();
  });

  it("shows KPI table with quote", async () => {
    wrap(<RecordingCard />);
    await waitFor(() =>
      expect(screen.getByText("greeting")).toBeInTheDocument()
    );
    expect(screen.getByText("Добрый день")).toBeInTheDocument();
  });

  it("shows segments with timecodes", async () => {
    wrap(<RecordingCard />);
    await waitFor(() =>
      expect(screen.getByText("Добрый день,")).toBeInTheDocument()
    );
  });
});

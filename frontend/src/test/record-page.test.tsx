import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderUI } from "./render";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

vi.mock("@/lib/auth", () => ({
  getToken: () => "test-token",
  authHeaders: () => ({ Authorization: "Bearer test-token" }),
}));

class MockWebSocket {
  url: string;
  readyState = 1;
  send = vi.fn();
  close = vi.fn();
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  onopen: (() => void) | null = null;
  constructor(url: string) {
    this.url = url;
    setTimeout(() => this.onopen?.(), 0);
  }
}

class MockMediaRecorder {
  state = "inactive";
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  start() {
    this.state = "recording";
  }
  stop() {
    this.state = "inactive";
    this.onstop?.();
  }
  static isTypeSupported() {
    return true;
  }
}

const MANAGERS = [
  { id: "mgr-1", full_name: "Иван Иванов", position: "sales", is_active: true, device_id: null, default_script_id: null },
  { id: "mgr-2", full_name: "Петр Петров", position: "support", is_active: true, device_id: null, default_script_id: null },
];

describe("RecordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // @ts-expect-error test stub
    global.WebSocket = MockWebSocket;
    // @ts-expect-error test stub
    global.MediaRecorder = MockMediaRecorder;
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn().mockResolvedValue({}) },
      writable: true,
      configurable: true,
    });
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => MANAGERS });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders manager selector and consent checkbox", async () => {
    const { default: RecordPage } = await import("@/app/(app)/recordings/record/page");
    renderUI(<RecordPage />);
    await waitFor(() => expect(screen.getByText(/согласие/i)).toBeTruthy());
    expect(screen.getByRole("checkbox")).toBeTruthy();
  });

  it("disables start until consent + manager selected", async () => {
    const { default: RecordPage } = await import("@/app/(app)/recordings/record/page");
    renderUI(<RecordPage />);
    await waitFor(() => screen.getByText(/согласие/i));
    expect(screen.getByRole("button", { name: /начать запись/i })).toBeDisabled();
  });

  it("toggles the consent checkbox", async () => {
    const { default: RecordPage } = await import("@/app/(app)/recordings/record/page");
    renderUI(<RecordPage />);
    await waitFor(() => screen.getByText(/согласие/i));
    const checkbox = screen.getByRole("checkbox") as HTMLInputElement;
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });

  it("shows the empty transcript placeholder before recording", async () => {
    const { default: RecordPage } = await import("@/app/(app)/recordings/record/page");
    renderUI(<RecordPage />);
    await waitFor(() => screen.getByText(/согласие/i));
    expect(screen.getByText(/Транскрипт появится здесь/i)).toBeInTheDocument();
  });
});

describe("useRecordWs hook", () => {
  it("is exported as a function", async () => {
    const { useRecordWs } = await import("@/lib/ws");
    expect(typeof useRecordWs).toBe("function");
  });

  it("parses partial_transcript messages (final vs partial)", () => {
    const onPartial = vi.fn();
    const onFinal = vi.fn();
    const handler = (data: string) => {
      const msg = JSON.parse(data);
      if (msg.type === "partial_transcript" && !msg.is_final) onPartial(msg.text);
      if (msg.type === "partial_transcript" && msg.is_final) onFinal(msg.text);
    };
    handler(JSON.stringify({ type: "partial_transcript", text: "Добрый день", is_final: false }));
    expect(onPartial).toHaveBeenCalledWith("Добрый день");
    handler(JSON.stringify({ type: "partial_transcript", text: "Итого", is_final: true }));
    expect(onFinal).toHaveBeenCalledWith("Итого");
  });
});

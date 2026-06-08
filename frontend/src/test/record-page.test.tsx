import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, waitFor, act } from "@testing-library/react";
import { renderUI } from "./render";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

vi.mock("@/lib/auth", () => ({
  getToken: () => "test-token",
  authHeaders: () => ({ Authorization: "Bearer test-token" }),
}));

class MockWebSocket {
  static last: MockWebSocket | null = null;
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
    MockWebSocket.last = this;
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

  it("explains that the user is redirected after recording (no live transcript)", async () => {
    const { default: RecordPage } = await import("@/app/(app)/recordings/record/page");
    renderUI(<RecordPage />);
    await waitFor(() => screen.getByText(/согласие/i));
    expect(screen.queryByText(/Транскрипт/i)).not.toBeInTheDocument();
    expect(screen.getByText(/перейдёте на страницу разговора автоматически/i)).toBeInTheDocument();
  });

  it("redirects to the recording pipeline once the final transcript arrives", async () => {
    MockWebSocket.last = null;
    const { default: RecordPage } = await import("@/app/(app)/recordings/record/page");
    renderUI(<RecordPage />);
    await waitFor(() => screen.getByText(/согласие/i));

    // consent + manager → enable start
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "mgr-1" } });
    fireEvent.click(screen.getByRole("button", { name: /начать запись/i }));

    // WS connects (onopen via setTimeout)
    await waitFor(() => expect(MockWebSocket.last).not.toBeNull());
    const ws = MockWebSocket.last!;

    // backend acks with the created recording id, then emits the final transcript
    act(() => {
      ws.onmessage?.({ data: JSON.stringify({ type: "ack", message: "recording rec-42 queued" }) });
      ws.onmessage?.({ data: JSON.stringify({ type: "partial_transcript", text: "Итоговый текст", is_final: true }) });
    });

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/recordings/rec-42"));
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

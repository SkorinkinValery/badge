import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderUI } from "./render";
import UploadRecordingPage from "@/app/(app)/recordings/upload/page";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

vi.mock("@/lib/auth", () => ({
  getToken: () => "admin-token",
  authHeaders: () => ({ Authorization: "Bearer admin-token" }),
  isAdmin: () => true,
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

const SAMPLE_MANAGERS = [
  { id: "mgr-1", full_name: "Иванов Иван", position: "Менеджер продаж", is_active: true, device_id: null, default_script_id: null },
  { id: "mgr-2", full_name: "Архивный", position: "Бывший", is_active: false, device_id: null, default_script_id: null },
];

const FILE = new File(["fake-audio-bytes"], "call.mp3", { type: "audio/mpeg" });

beforeEach(() => {
  mockPush.mockClear();
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url === "/api/managers") {
      return Promise.resolve({ ok: true, json: async () => SAMPLE_MANAGERS });
    }
    return Promise.resolve({ ok: true, json: async () => ({ recording_id: "rec-123", status: "queued" }) });
  });
});

async function fillForm() {
  await waitFor(() => expect(screen.getByText("Иванов Иван (Менеджер продаж)")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText(/менеджер/i), { target: { value: "mgr-1" } });
  fireEvent.click(screen.getByLabelText(/согласие клиента/i));
  const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(fileInput, { target: { files: [FILE] } });
}

describe("Upload recording page", () => {
  it("only lists active managers", async () => {
    renderUI(<UploadRecordingPage />);
    await waitFor(() => expect(screen.getByText("Иванов Иван (Менеджер продаж)")).toBeInTheDocument());
    expect(screen.queryByText(/Архивный/)).not.toBeInTheDocument();
  });

  it("disables submit until manager, consent and file are set", async () => {
    renderUI(<UploadRecordingPage />);
    await waitFor(() => expect(screen.getByText("Иванов Иван (Менеджер продаж)")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /загрузить запись/i })).toBeDisabled();
    await fillForm();
    await waitFor(() => expect(screen.getByRole("button", { name: /загрузить запись/i })).toBeEnabled());
  });

  it("submits the form via POST /api/uploads and redirects to the recording page", async () => {
    renderUI(<UploadRecordingPage />);
    await fillForm();
    await waitFor(() => expect(screen.getByRole("button", { name: /загрузить запись/i })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: /загрузить запись/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/recordings/rec-123"));

    const uploadCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.find(
      (call: unknown[]) => call[0] === "/api/uploads",
    );
    expect(uploadCall).toBeTruthy();
    const [, options] = uploadCall as [string, RequestInit];
    expect(options.method).toBe("POST");
    const form = options.body as FormData;
    expect(form.get("manager_id")).toBe("mgr-1");
    expect(form.get("consent_flag")).toBe("true");
    expect(form.get("file")).toBeInstanceOf(File);
  });

  it("shows an error message when the upload fails", async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/managers") {
        return Promise.resolve({ ok: true, json: async () => SAMPLE_MANAGERS });
      }
      return Promise.resolve({ ok: false, status: 422, json: async () => ({ detail: "consent_flag is required for recordings" }) });
    });

    renderUI(<UploadRecordingPage />);
    await fillForm();
    await waitFor(() => expect(screen.getByRole("button", { name: /загрузить запись/i })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: /загрузить запись/i }));

    await waitFor(() => expect(screen.getByText("consent_flag is required for recordings")).toBeInTheDocument());
    expect(mockPush).not.toHaveBeenCalled();
  });
});

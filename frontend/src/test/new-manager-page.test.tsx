import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderUI } from "./render";
import NewManagerPage from "@/app/(app)/admin/managers/new/page";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

vi.mock("@/lib/auth", () => ({
  getToken: () => "admin-token",
  authHeaders: () => ({ Authorization: "Bearer admin-token" }),
  isAdmin: () => true,
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

function wrap(ui: React.ReactElement) {
  return renderUI(ui);
}

const SAMPLE_SCRIPTS = [
  { id: "scr-1", name: "Базовый скрипт продаж", is_active: true },
  { id: "scr-2", name: "Архивный скрипт", is_active: false },
];

beforeEach(() => {
  mockPush.mockClear();
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url === "/api/scripts") {
      return Promise.resolve({ ok: true, json: async () => SAMPLE_SCRIPTS });
    }
    return Promise.resolve({
      ok: true,
      json: async () => ({ id: "mgr-new", full_name: "Сидоров Сидор", position: "Менеджер" }),
    });
  });
});

async function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/ФИО/i), {
    target: { value: "Сидоров Сидор" },
  });
  fireEvent.change(screen.getByLabelText(/должность/i), {
    target: { value: "Менеджер продаж" },
  });
}

describe("New manager page", () => {
  it("only lists active scripts", async () => {
    wrap(<NewManagerPage />);
    await waitFor(() =>
      expect(screen.getByText("Базовый скрипт продаж")).toBeInTheDocument()
    );
    expect(screen.queryByText(/Архивный скрипт/)).not.toBeInTheDocument();
  });

  it("disables submit until required fields are filled", async () => {
    wrap(<NewManagerPage />);
    expect(screen.getByRole("button", { name: /создать менеджера/i })).toBeDisabled();
    await fillRequiredFields();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /создать менеджера/i })).toBeEnabled()
    );
  });

  it("submits the form via POST /api/managers and redirects to the list", async () => {
    wrap(<NewManagerPage />);
    await fillRequiredFields();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /создать менеджера/i })).toBeEnabled()
    );
    fireEvent.click(screen.getByRole("button", { name: /создать менеджера/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/admin/managers"));

    const createCall = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.find(
      (call: unknown[]) => call[0] === "/api/managers"
    );
    expect(createCall).toBeTruthy();
    const [, options] = createCall as [string, RequestInit];
    expect(options.method).toBe("POST");
    const payload = JSON.parse(options.body as string);
    expect(payload.full_name).toBe("Сидоров Сидор");
    expect(payload.position).toBe("Менеджер продаж");
    expect(payload.device_id).toBeNull();
    expect(payload.default_script_id).toBeNull();
  });

  it("shows an error message when creation fails", async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/scripts") {
        return Promise.resolve({ ok: true, json: async () => SAMPLE_SCRIPTS });
      }
      return Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({ detail: "device_id already in use" }),
      });
    });

    wrap(<NewManagerPage />);
    await fillRequiredFields();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /создать менеджера/i })).toBeEnabled()
    );
    fireEvent.click(screen.getByRole("button", { name: /создать менеджера/i }));

    await waitFor(() =>
      expect(screen.getByText("device_id already in use")).toBeInTheDocument()
    );
    expect(mockPush).not.toHaveBeenCalled();
  });
});

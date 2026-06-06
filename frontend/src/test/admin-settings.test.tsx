import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import SettingsPage from "@/app/admin/settings/page";

vi.mock("@/lib/auth", () => ({
  getToken: () => "admin-token",
  authHeaders: () => ({ Authorization: "Bearer admin-token" }),
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function wrap(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

const SAMPLE_SETTINGS = {
  active_crm: "json",
  available_providers: ["bitrix24", "google_sheets", "json", "webhook"],
  params: {},
};

beforeEach(() => {
  global.fetch = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
    if (url.includes("/api/admin/settings") && (!opts?.method || opts.method === "GET")) {
      return Promise.resolve({ ok: true, json: async () => SAMPLE_SETTINGS });
    }
    if (url.includes("/api/admin/settings") && opts?.method === "PUT") {
      const body = JSON.parse(opts.body as string);
      return Promise.resolve({ ok: true, json: async () => ({ ...SAMPLE_SETTINGS, ...body }) });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  });
});

describe("CRM Settings page", () => {
  it("renders page title", async () => {
    wrap(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText(/настройки crm/i)).toBeInTheDocument()
    );
  });

  it("shows active CRM provider", async () => {
    wrap(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByText("json")).toBeInTheDocument()
    );
  });

  it("shows save button", async () => {
    wrap(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /сохранить/i })).toBeInTheDocument()
    );
  });

  it("calls PUT on save", async () => {
    wrap(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /сохранить/i })).toBeInTheDocument()
    );
    await userEvent.click(screen.getByRole("button", { name: /сохранить/i }));
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/admin/settings"),
        expect.objectContaining({ method: "PUT" })
      )
    );
  });

  it("shows success alert after save", async () => {
    wrap(<SettingsPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /сохранить/i })).toBeInTheDocument()
    );
    await userEvent.click(screen.getByRole("button", { name: /сохранить/i }));
    await waitFor(() =>
      expect(screen.getByText(/сохранены/i)).toBeInTheDocument()
    );
  });
});

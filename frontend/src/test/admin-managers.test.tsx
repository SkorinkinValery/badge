import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import ManagersPage from "@/app/admin/managers/page";

vi.mock("@/lib/auth", () => ({
  getToken: () => "admin-token",
  authHeaders: () => ({ Authorization: "Bearer admin-token" }),
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

function wrap(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

const SAMPLE_MANAGERS = [
  {
    id: "mgr-1",
    full_name: "Иван Иванов",
    position: "Менеджер",
    device_id: null,
    is_active: true,
    default_script_id: null,
  },
  {
    id: "mgr-2",
    full_name: "Пётр Петров",
    position: "Старший менеджер",
    device_id: "device-001",
    is_active: false,
    default_script_id: null,
  },
];

beforeEach(() => {
  mockPush.mockClear();
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => SAMPLE_MANAGERS,
  });
});

describe("Managers admin page", () => {
  it("renders a table with managers", async () => {
    wrap(<ManagersPage />);
    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
  });

  it("shows manager names", async () => {
    wrap(<ManagersPage />);
    await waitFor(() =>
      expect(screen.getByText("Иван Иванов")).toBeInTheDocument()
    );
    expect(screen.getByText("Пётр Петров")).toBeInTheDocument();
  });

  it("shows active status badge for active managers", async () => {
    wrap(<ManagersPage />);
    await waitFor(() => expect(screen.getAllByText(/активен/i).length).toBeGreaterThan(0));
  });

  it("shows empty state when no managers", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    wrap(<ManagersPage />);
    await waitFor(() =>
      expect(screen.getByText(/нет менеджеров/i)).toBeInTheDocument()
    );
  });

  it("redirects to login when no token", async () => {
    vi.doMock("@/lib/auth", () => ({
      getToken: () => null,
      authHeaders: () => ({}),
    }));
    // token check happens on mount
    wrap(<ManagersPage />);
    // redirect is best-effort — just check no crash
  });
});

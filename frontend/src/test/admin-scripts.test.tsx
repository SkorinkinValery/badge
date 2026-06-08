import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderUI } from "./render";
import ScriptsPage from "@/app/(app)/admin/scripts/page";

vi.mock("@/lib/auth", () => ({
  getToken: () => "admin-token",
  authHeaders: () => ({ Authorization: "Bearer admin-token" }),
  isAdmin: () => true,
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function wrap(ui: React.ReactElement) {
  return renderUI(ui);
}

const SAMPLE_SCRIPTS = [
  {
    id: "script-1",
    name: "Основной скрипт",
    is_active: true,
    active_version_id: "ver-1",
  },
  {
    id: "script-2",
    name: "Скрипт для B2B",
    is_active: true,
    active_version_id: "ver-3",
  },
];

beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => SAMPLE_SCRIPTS,
  });
});

describe("Scripts admin page", () => {
  it("renders a list of scripts", async () => {
    wrap(<ScriptsPage />);
    await waitFor(() =>
      expect(screen.getByText("Основной скрипт")).toBeInTheDocument()
    );
  });

  it("shows all script names", async () => {
    wrap(<ScriptsPage />);
    await waitFor(() => {
      expect(screen.getByText("Основной скрипт")).toBeInTheDocument();
      expect(screen.getByText("Скрипт для B2B")).toBeInTheDocument();
    });
  });

  it("shows upload button", async () => {
    wrap(<ScriptsPage />);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /новый скрипт/i })
      ).toBeInTheDocument()
    );
  });

  it("shows empty state when no scripts", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    wrap(<ScriptsPage />);
    await waitFor(() =>
      expect(screen.getByText(/нет скриптов/i)).toBeInTheDocument()
    );
  });

  it("shows active version indicator", async () => {
    wrap(<ScriptsPage />);
    await waitFor(() =>
      expect(screen.getAllByText(/активная версия/i).length).toBeGreaterThan(0)
    );
  });
});

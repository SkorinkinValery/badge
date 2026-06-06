import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";

// ── Mocks ────────────────────────────────────────────────────────────────────

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

// Default: no token, no role
vi.mock("@/lib/auth", () => ({
  getToken: vi.fn(() => null),
  getRole: vi.fn(() => null),
  clearToken: vi.fn(),
}));

import { getToken, getRole } from "@/lib/auth";
import AppLayout from "@/app/(app)/layout";

function wrap(children: React.ReactNode) {
  return render(
    <MantineProvider>
      <AppLayout>{children}</AppLayout>
    </MantineProvider>
  );
}

beforeEach(() => {
  mockReplace.mockClear();
  vi.mocked(getToken).mockReturnValue(null);
  vi.mocked(getRole).mockReturnValue(null);
});

describe("AppLayout — auth guard", () => {
  it("redirects to /login when no token", async () => {
    vi.mocked(getToken).mockReturnValue(null);
    wrap(<div>protected</div>);
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/login");
    });
  });

  it("does not render children while token is absent", () => {
    vi.mocked(getToken).mockReturnValue(null);
    wrap(<div>secret content</div>);
    expect(screen.queryByText("secret content")).not.toBeInTheDocument();
  });

  it("renders children when token is present", async () => {
    vi.mocked(getToken).mockReturnValue("valid-token");
    vi.mocked(getRole).mockReturnValue("viewer");
    wrap(<div>protected content</div>);
    await waitFor(() => {
      expect(screen.getByText("protected content")).toBeInTheDocument();
    });
  });
});

describe("AppLayout — role-based menu", () => {
  it("hides admin menu items for viewer role", async () => {
    vi.mocked(getToken).mockReturnValue("viewer-token");
    vi.mocked(getRole).mockReturnValue("viewer");
    wrap(<div />);
    await waitFor(() => {
      expect(screen.getByText("Аудиобейдж")).toBeInTheDocument();
    });
    expect(screen.queryByText("Менеджеры")).not.toBeInTheDocument();
    expect(screen.queryByText("Скрипты")).not.toBeInTheDocument();
    expect(screen.queryByText("Дневная сводка")).not.toBeInTheDocument();
    expect(screen.queryByText("Настройки")).not.toBeInTheDocument();
  });

  it("shows admin menu items for admin role", async () => {
    vi.mocked(getToken).mockReturnValue("admin-token");
    vi.mocked(getRole).mockReturnValue("admin");
    wrap(<div />);
    await waitFor(() => {
      expect(screen.getByText("Менеджеры")).toBeInTheDocument();
    });
    expect(screen.getByText("Скрипты")).toBeInTheDocument();
    expect(screen.getByText("Дневная сводка")).toBeInTheDocument();
    expect(screen.getByText("Настройки")).toBeInTheDocument();
  });

  it("always shows Звонки navigation items", async () => {
    vi.mocked(getToken).mockReturnValue("viewer-token");
    vi.mocked(getRole).mockReturnValue("viewer");
    wrap(<div />);
    await waitFor(() => {
      expect(screen.getByText("Записи")).toBeInTheDocument();
    });
    expect(screen.getByText("Запись с микрофона")).toBeInTheDocument();
  });
});

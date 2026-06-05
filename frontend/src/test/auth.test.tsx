import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import LoginPage from "@/app/(auth)/login/page";
import { storeToken, getToken, clearToken } from "@/lib/auth";

function renderWithMantine(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

beforeEach(() => {
  clearToken();
  mockPush.mockClear();
});

describe("Login page", () => {
  it("renders login form", () => {
    renderWithMantine(<LoginPage />);
    expect(screen.getByRole("textbox", { name: /логин/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/пароль/i)).toBeInTheDocument();
  });

  it("submits credentials and redirects on success", async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: "tok123", token_type: "bearer" }),
    });

    renderWithMantine(<LoginPage />);
    fireEvent.change(screen.getByRole("textbox", { name: /логин/i }), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/пароль/i), {
      target: { value: "adminpass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /войти/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/recordings"));
    expect(getToken()).toBe("tok123");
  });

  it("shows error on failed login", async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "Invalid credentials" }),
    });

    renderWithMantine(<LoginPage />);
    fireEvent.change(screen.getByRole("textbox", { name: /логин/i }), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/пароль/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /войти/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument()
    );
  });

  it("clears token on clearToken", () => {
    storeToken("abc");
    expect(getToken()).toBe("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });

  it("stores and retrieves token", () => {
    storeToken("my-jwt-token");
    expect(getToken()).toBe("my-jwt-token");
  });
});

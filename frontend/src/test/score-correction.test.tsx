import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import ScoreCorrectionForm from "@/components/ScoreCorrectionForm";

vi.mock("@/lib/auth", () => ({
  getToken: () => "test-token",
  authHeaders: () => ({ Authorization: "Bearer test-token" }),
  storeToken: vi.fn(),
  clearToken: vi.fn(),
}));

function wrap(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

const defaultProps = {
  recordingId: "aaa-111",
  currentScore: 75.0,
  autoScore: 75.0,
  currentVerdict: "~",
};

beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ...defaultProps, score: 90.0, verdict: "+", auto_score: 75.0 }),
  });
});

describe("ScoreCorrectionForm", () => {
  it("shows auto_score as original score", () => {
    wrap(<ScoreCorrectionForm {...defaultProps} onSaved={vi.fn()} />);
    expect(screen.getByText(/75/)).toBeInTheDocument();
  });

  it("renders score input and submit button", () => {
    wrap(<ScoreCorrectionForm {...defaultProps} onSaved={vi.fn()} />);
    expect(screen.getByLabelText(/оценка/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /сохранить/i })).toBeInTheDocument();
  });

  it("sends PATCH request on submit", async () => {
    const onSaved = vi.fn();
    wrap(<ScoreCorrectionForm {...defaultProps} onSaved={onSaved} />);

    fireEvent.change(screen.getByLabelText(/оценка/i), {
      target: { value: "90" },
    });
    fireEvent.click(screen.getByRole("button", { name: /сохранить/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/recordings/aaa-111/analysis"),
        expect.objectContaining({ method: "PATCH" })
      );
    });
  });

  it("calls onSaved after successful save", async () => {
    const onSaved = vi.fn();
    wrap(<ScoreCorrectionForm {...defaultProps} onSaved={onSaved} />);

    fireEvent.change(screen.getByLabelText(/оценка/i), {
      target: { value: "90" },
    });
    fireEvent.click(screen.getByRole("button", { name: /сохранить/i }));

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it("shows error when save fails", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Forbidden" }),
    });
    wrap(<ScoreCorrectionForm {...defaultProps} onSaved={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /сохранить/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument()
    );
  });
});

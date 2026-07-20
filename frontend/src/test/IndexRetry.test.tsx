import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import Index from "@/pages/Index";
import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";

// Stub the screens down to the wiring we're testing: Index's submit /
// retry flow (PROJECT_PLAN §3.2.1 — a failed submit must not lose answers).
vi.mock("@/components/UsernameScreen", () => ({
  default: ({ onSubmit }: { onSubmit: (n: string) => void }) => (
    <button onClick={() => onSubmit("Kid")}>stub-login</button>
  ),
}));
vi.mock("@/components/SetupScreen", () => ({
  default: ({ onStart }: { onStart: (g: string, m: string, d: string, a: string) => void }) => (
    <button onClick={() => onStart("3", "addition", "easy", "typing")}>stub-start</button>
  ),
}));
vi.mock("@/components/QuizScreen", () => ({
  default: ({ onFinish }: { onFinish: (a: (string | null)[], t: number) => void }) => (
    <button onClick={() => onFinish(Array(10).fill("7"), 42)}>stub-finish</button>
  ),
}));
vi.mock("@/components/ResultsScreen", () => ({
  default: () => <p>stub-results</p>,
}));
vi.mock("@/components/ProgressScreen", () => ({
  default: () => <p>stub-progress</p>,
}));

const quiz = {
  id: "quiz-1", username: "Kid", grade: "3", mathType: "addition", difficulty: "easy",
  questions: [], createdAt: "2026-01-01T00:00:00Z",
};

const result = {
  quizId: "quiz-1", username: "Kid", score: 10, total: 10, timeUsedSeconds: 42,
  badge: "🏆", results: [], submittedAt: "2026-01-01T00:00:00Z",
};

async function playToSubmit() {
  render(<Index />);
  fireEvent.click(screen.getByText("stub-login"));
  fireEvent.click(screen.getByText("stub-start"));
  await waitFor(() => expect(screen.getByText("stub-finish")).toBeInTheDocument());
  fireEvent.click(screen.getByText("stub-finish"));
}

describe("Index submit retry (§3.2.1)", () => {
  beforeEach(() => {
    vi.spyOn(api, "createQuiz").mockResolvedValue(quiz as never);
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("offers Try again after a network failure and resubmits the same answers", async () => {
    const submitSpy = vi
      .spyOn(api, "submitQuiz")
      .mockRejectedValueOnce(new ApiError(0, "unknown_error", "boom"))
      .mockResolvedValueOnce(result as never);

    await playToSubmit();

    await waitFor(() => expect(screen.getByText(/they're safe/)).toBeInTheDocument());
    fireEvent.click(screen.getByText("🔄 Try again"));

    await waitFor(() => expect(screen.getByText("stub-results")).toBeInTheDocument());
    expect(submitSpy).toHaveBeenCalledTimes(2);
    // Both attempts carry the identical payload.
    expect(submitSpy.mock.calls[0]).toEqual(submitSpy.mock.calls[1]);
  });

  it("does not offer a retry when the quiz was already submitted", async () => {
    vi.spyOn(api, "submitQuiz").mockRejectedValue(
      new ApiError(409, "already_submitted", "already"),
    );

    await playToSubmit();

    await waitFor(() => expect(screen.getByText(/already turned in/)).toBeInTheDocument());
    expect(screen.queryByText("🔄 Try again")).toBeNull();
    expect(screen.getByText("🏠 Back Home")).toBeInTheDocument();
  });
});

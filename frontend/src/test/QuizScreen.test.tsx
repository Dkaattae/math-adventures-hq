import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, cleanup } from "@testing-library/react";
import QuizScreen from "@/components/QuizScreen";
import type { Question } from "@/lib/api";

// Render framer-motion elements as plain tags — exit animations never
// complete under fake timers, which would strand AnimatePresence content.
vi.mock("framer-motion", async () => {
  const React = await import("react");
  const strip = (props: Record<string, unknown>) => {
    const { initial, animate, exit, transition, whileHover, whileTap, ...rest } = props;
    return rest;
  };
  return {
    motion: new Proxy({}, {
      get: (_target, tag) =>
        ({ children, ...props }: { children?: React.ReactNode }) =>
          React.createElement(String(tag), strip(props), children),
    }),
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => children,
  };
});

const questions: Question[] = Array.from({ length: 10 }, (_, i) => ({
  id: i,
  question: `Question ${i}?`,
}));

describe("QuizScreen timers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("keeps the total countdown running while the player types", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} />);

    const input = screen.getByPlaceholderText("Your answer...");
    // Type a keystroke every 400ms for 8 seconds — faster than the old
    // 1s interval could ever fire between teardowns.
    for (let i = 0; i < 20; i++) {
      fireEvent.change(input, { target: { value: `4${i}` } });
      await act(() => vi.advanceTimersByTimeAsync(400));
    }

    // 8s elapsed → total shows 2:52; before the fix it stayed at 3:00.
    expect(screen.getByText(/2:5[0-4] left/)).toBeInTheDocument();
  });

  it("advances to the next question when the per-question timer expires", async () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} />);

    expect(screen.getByText("Question 1 of 10")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(15_500));
    expect(screen.getByText("Question 2 of 10")).toBeInTheDocument();
  });

  it("keeps a typed-but-unsubmitted answer when the question timer expires", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} />);

    const input = screen.getByPlaceholderText("Your answer...");
    fireEvent.change(input, { target: { value: "42" } });
    // Let question 1 time out, then finish the quiz immediately.
    await act(() => vi.advanceTimersByTimeAsync(15_500));
    fireEvent.click(screen.getByText("Finish ✅"));

    expect(onFinish).toHaveBeenCalledTimes(1);
    const [answers] = onFinish.mock.calls[0];
    expect(answers[0]).toBe("42");
  });

  it("finishes the quiz when the timer expires on the last question", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} />);

    // Jump to the last question via the review panel.
    fireEvent.click(screen.getByText("📋 Review"));
    fireEvent.click(screen.getByRole("button", { name: "10" }));
    expect(screen.getByText("Question 10 of 10")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Your answer..."), { target: { value: "7" } });
    await act(() => vi.advanceTimersByTimeAsync(15_500));

    expect(onFinish).toHaveBeenCalledTimes(1);
    const [answers] = onFinish.mock.calls[0];
    expect(answers[9]).toBe("7");
  });

  it("finishes exactly once when the total time runs out", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} />);

    await act(() => vi.advanceTimersByTimeAsync(181_000));
    expect(onFinish).toHaveBeenCalledTimes(1);
    const [, timeUsed] = onFinish.mock.calls[0];
    expect(timeUsed).toBe(180);
  });
});

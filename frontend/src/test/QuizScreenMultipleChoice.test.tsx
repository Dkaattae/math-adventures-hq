import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import QuizScreen from "@/components/QuizScreen";
import type { Question } from "@/lib/api";

vi.mock("framer-motion", async () => {
  const React = await import("react");
  const strip = (props: Record<string, unknown>) => {
    const { initial, animate, exit, transition, whileHover, whileTap, ...rest } = props;
    return rest;
  };
  return {
    motion: new Proxy({}, {
      get: (_t, tag) =>
        ({ children, ...props }: { children?: React.ReactNode }) =>
          React.createElement(String(tag), strip(props), children),
    }),
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => children,
  };
});

const mcQuestions: Question[] = Array.from({ length: 10 }, (_, i) => ({
  id: i,
  question: `Question ${i}?`,
  options: [`${i}a`, `${i}b`, `${i}c`, `${i}d`],
}));

describe("QuizScreen multiple-choice mode", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("renders option buttons and no text input or Submit button", () => {
    render(<QuizScreen questions={mcQuestions} onFinish={vi.fn()} />);
    expect(screen.queryByPlaceholderText("Your answer...")).toBeNull();
    expect(screen.queryByText("Submit Answer")).toBeNull();
    expect(screen.getByRole("button", { name: "0a" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "0d" })).toBeInTheDocument();
  });

  it("records the chosen option and advances to the next question", async () => {
    render(<QuizScreen questions={mcQuestions} onFinish={vi.fn()} />);
    expect(screen.getByText("Question 1 of 10")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "0b" }));
    await act(() => vi.advanceTimersByTimeAsync(500));

    expect(screen.getByText("Question 2 of 10")).toBeInTheDocument();
  });

  it("submits the chosen options when finishing", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={mcQuestions} onFinish={onFinish} />);

    fireEvent.click(screen.getByRole("button", { name: "0c" }));
    await act(() => vi.advanceTimersByTimeAsync(500));
    fireEvent.click(screen.getByText("Finish ✅"));

    expect(onFinish).toHaveBeenCalledTimes(1);
    const [answers] = onFinish.mock.calls[0];
    expect(answers[0]).toBe("0c");
  });
});

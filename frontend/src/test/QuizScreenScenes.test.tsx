import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import QuizScreen from "@/components/QuizScreen";
import type { Question } from "@/lib/api";

// Word problems arrive as multi-line scenes with their own clocks: a
// five-line shopping list can't be read in the 15 seconds a "7 + 5" gets.

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

const SCENE = "Maya's shopping list:\n\n• 4 apples\n• 2 bagels\n\nHow many come from the produce aisle?";

const plain = (): Question[] =>
  Array.from({ length: 10 }, (_, i) => ({ id: i, question: `Question ${i}?` }));

const scenes = (seconds = 60): Question[] =>
  Array.from({ length: 10 }, (_, i) => ({
    id: i,
    question: `${SCENE} (${i})`,
    timeLimitSeconds: seconds,
  }));

describe("QuizScreen scene questions", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("keeps the line breaks of a multi-line scene", () => {
    render(<QuizScreen questions={scenes()} onFinish={vi.fn()} onQuit={vi.fn()} />);
    const text = screen.getByText(/shopping list/);
    expect(text.className).toContain("whitespace-pre-line");
    expect(text.textContent).toContain("• 4 apples");
  });

  it("gives each question the clock the server sent", async () => {
    render(<QuizScreen questions={scenes(60)} onFinish={vi.fn()} onQuit={vi.fn()} />);
    expect(screen.getByText("⏱ 60s")).toBeInTheDocument();

    // Still on question 1 well past the old 15-second limit.
    await act(() => vi.advanceTimersByTimeAsync(20_000));
    expect(screen.getByText("Question 1 of 10")).toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(41_000));
    expect(screen.getByText("Question 2 of 10")).toBeInTheDocument();
  });

  it("scales the whole-quiz clock to the questions in it", () => {
    render(<QuizScreen questions={scenes(60)} onFinish={vi.fn()} onQuit={vi.fn()} />);
    // 10 × 60 + 30 slack = 630s = 10:30.
    expect(screen.getByText(/10:30 left/)).toBeInTheDocument();
  });

  it("leaves plain questions on the original 15s / 3:00 budget", () => {
    render(<QuizScreen questions={plain()} onFinish={vi.fn()} onQuit={vi.fn()} />);
    expect(screen.getByText("⏱ 15s")).toBeInTheDocument();
    expect(screen.getByText(/3:00 left/)).toBeInTheDocument();
  });

  it("still auto-submits when a scene quiz runs out of time", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={scenes(60)} onFinish={onFinish} onQuit={vi.fn()} />);
    await act(() => vi.advanceTimersByTimeAsync(631_000));
    expect(onFinish).toHaveBeenCalledTimes(1);
  });
});

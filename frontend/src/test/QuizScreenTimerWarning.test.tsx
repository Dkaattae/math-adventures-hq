import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import QuizScreen from "@/components/QuizScreen";
import type { Question } from "@/lib/api";

// The whole-quiz clock auto-submits at 0:00, so the last 30 seconds get
// a visible *and* readable warning (PROJECT_PLAN §3.1), and the answer
// input asks for the keyboard that fits the answer (§3.2).

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

const questions = (extra: Partial<Question> = {}): Question[] =>
  Array.from({ length: 10 }, (_, i) => ({ id: i, question: `Question ${i}?`, ...extra }));

const warning = () => screen.queryByText(/Less than 30 seconds left/);
const input = () => screen.getByPlaceholderText("Your answer...");

describe("QuizScreen total-time warning", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("stays quiet while there's plenty of time", async () => {
    render(<QuizScreen questions={questions()} onFinish={vi.fn()} onQuit={vi.fn()} />);
    await act(() => vi.advanceTimersByTimeAsync(60_000)); // 2:00 left
    expect(warning()).toBeNull();
    expect(screen.getByText(/2:00 left/)).toBeInTheDocument();
  });

  it("warns in words for the last 30 seconds", async () => {
    render(<QuizScreen questions={questions()} onFinish={vi.fn()} onQuit={vi.fn()} />);
    await act(() => vi.advanceTimersByTimeAsync(150_000)); // 0:30 left

    const alert = warning();
    expect(alert).toBeInTheDocument();
    // Announced to screen readers, not signalled by colour alone.
    expect(alert).toHaveAttribute("role", "status");
    expect(screen.getByText(/⏰ 0:2\d left|⏰ 0:30 left/)).toBeInTheDocument();
  });

  it("still auto-submits when the clock runs out", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions()} onFinish={onFinish} onQuit={vi.fn()} />);
    await act(() => vi.advanceTimersByTimeAsync(181_000));
    expect(onFinish).toHaveBeenCalledTimes(1);
  });
});

describe("QuizScreen answer keyboard", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it.each([
    ["integer", "numeric"],
    ["decimal", "decimal"],
    ["text", "text"],
  ] as const)("asks for the %s keypad", (answerKind, expected) => {
    render(<QuizScreen questions={questions({ answerKind })} onFinish={vi.fn()} onQuit={vi.fn()} />);
    expect(input()).toHaveAttribute("inputmode", expected);
  });

  it("falls back to the full keyboard when the server sends no kind", () => {
    render(<QuizScreen questions={questions()} onFinish={vi.fn()} onQuit={vi.fn()} />);
    expect(input()).toHaveAttribute("inputmode", "text");
  });

  it("keeps type=text so fractions and '<' can still be typed", () => {
    render(<QuizScreen questions={questions({ answerKind: "integer" })} onFinish={vi.fn()} onQuit={vi.fn()} />);
    expect(input()).toHaveAttribute("type", "text");
  });
});

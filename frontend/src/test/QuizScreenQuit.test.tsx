/**
 * PROJECT_PLAN §3.4: a quiz you can leave.
 *
 * Before this, Finish (which submits) and the expiring clock were the
 * only exits, so a kid who picked grade 5 by mistake had to sit through
 * ten questions they couldn't read. Leaving is destructive — the
 * attempt is thrown away — so it asks first and never submits.
 */
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

const questions: Question[] = Array.from({ length: 10 }, (_, i) => ({
  id: i,
  question: `Question ${i}?`,
}));

const quitButton = () => screen.getByRole("button", { name: "Quit this quiz" });
const leave = () => screen.getByText("Leave 🚪");
const dialog = () => screen.queryByRole("dialog");

describe("QuizScreen quit", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("offers a way out from the first question", () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} onQuit={vi.fn()} />);
    expect(quitButton()).toBeInTheDocument();
  });

  it("asks before leaving instead of quitting on the first tap", () => {
    const onQuit = vi.fn();
    render(<QuizScreen questions={questions} onFinish={vi.fn()} onQuit={onQuit} />);

    expect(dialog()).toBeNull();
    fireEvent.click(quitButton());
    expect(dialog()).toBeInTheDocument();
    expect(onQuit).not.toHaveBeenCalled();
  });

  it("says the attempt won't be saved", () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} onQuit={vi.fn()} />);
    fireEvent.click(quitButton());
    expect(screen.getByText(/won't be saved/)).toBeInTheDocument();
  });

  it("'Keep playing' puts them back on the same question", () => {
    const onQuit = vi.fn();
    render(<QuizScreen questions={questions} onFinish={vi.fn()} onQuit={onQuit} />);

    fireEvent.click(quitButton());
    fireEvent.click(screen.getByText("Keep playing 💪"));
    expect(dialog()).toBeNull();
    expect(onQuit).not.toHaveBeenCalled();
    expect(screen.getByText("Question 1 of 10")).toBeInTheDocument();
  });

  it("leaves once confirmed — and never submits the answers", () => {
    const onFinish = vi.fn();
    const onQuit = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} onQuit={onQuit} />);

    fireEvent.change(screen.getByPlaceholderText("Your answer..."), {
      target: { value: "42" },
    });
    fireEvent.click(quitButton());
    fireEvent.click(leave());

    expect(onQuit).toHaveBeenCalledTimes(1);
    expect(onFinish).not.toHaveBeenCalled();
  });

  it("the countdown can't submit a quiz that was already abandoned", async () => {
    const onFinish = vi.fn();
    const onQuit = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} onQuit={onQuit} />);

    fireEvent.click(quitButton());
    fireEvent.click(leave());
    // The parent unmounts us on quit, but until it does the interval is
    // still ticking — running out the whole clock must stay silent.
    await act(() => vi.advanceTimersByTimeAsync(200_000));

    expect(onFinish).not.toHaveBeenCalled();
    expect(onQuit).toHaveBeenCalledTimes(1);
  });

  it("finishing after quitting is refused, not double-counted", () => {
    const onFinish = vi.fn();
    const onQuit = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} onQuit={onQuit} />);

    // Answer everything, so Finish would submit straight away.
    for (let i = 0; i < 10; i++) {
      fireEvent.change(screen.getByPlaceholderText("Your answer..."), {
        target: { value: String(i) },
      });
      if (i < 9) fireEvent.click(screen.getByText("Next →"));
    }
    fireEvent.click(quitButton());
    fireEvent.click(leave());
    fireEvent.click(screen.getByText("Finish ✅"));

    expect(onFinish).not.toHaveBeenCalled();
  });
});

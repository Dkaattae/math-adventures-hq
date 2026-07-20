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

const input = () => screen.getByPlaceholderText("Your answer...") as HTMLInputElement;
const type = (value: string) => fireEvent.change(input(), { target: { value } });

describe("QuizScreen navigation (review-before-submit model)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("Next saves the typed draft instead of discarding it", () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} />);

    type("42");
    fireEvent.click(screen.getByText("Next →"));
    expect(screen.getByText("Question 2 of 10")).toBeInTheDocument();

    fireEvent.click(screen.getByText("← Back"));
    expect(input().value).toBe("42");
    // The dot reflects the saved answer too.
    expect(screen.getByRole("button", { name: /Question 1, answered/ })).toBeInTheDocument();
  });

  it("has no Back button on the first question and no Next on the last", () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} />);

    expect(screen.queryByText("← Back")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Question 10, blank/ }));
    expect(screen.queryByText("Next →")).toBeNull();
    expect(screen.getByText("Finish ✅")).toBeInTheDocument();
  });

  it("dots jump directly to a question, saving the draft on the way out", () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} />);

    type("7");
    fireEvent.click(screen.getByRole("button", { name: /Question 5, blank/ }));
    expect(screen.getByText("Question 5 of 10")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Question 1, answered/ })).toBeInTheDocument();
  });

  it("hides Finish until the last question or a fully answered quiz", () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} />);
    expect(screen.queryByText("Finish ✅")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Question 10, blank/ }));
    expect(screen.getByText("Finish ✅")).toBeInTheDocument();
  });

  it("shows Finish anywhere once every question is answered", () => {
    render(<QuizScreen questions={questions} onFinish={vi.fn()} />);

    for (let i = 0; i < 10; i++) {
      type(String(i));
      if (i < 9) fireEvent.click(screen.getByText("Next →"));
    }
    // Walk back to the middle — Finish stays available.
    fireEvent.click(screen.getByRole("button", { name: /Question 5, answered/ }));
    expect(screen.getByText("Finish ✅")).toBeInTheDocument();
  });

  it("finishes immediately when nothing is blank", () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} />);

    for (let i = 0; i < 10; i++) {
      type(String(i));
      if (i < 9) fireEvent.click(screen.getByText("Next →"));
    }
    fireEvent.click(screen.getByText("Finish ✅"));
    expect(screen.queryByText(/blank question/)).toBeNull();
    expect(onFinish).toHaveBeenCalledTimes(1);
    const [answers] = onFinish.mock.calls[0];
    expect(answers).toEqual(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]);
  });

  it("'Keep going' jumps to the first blank question", () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} />);

    // Answer Q1 and Q3, leave Q2 blank, go to the end.
    type("1");
    fireEvent.click(screen.getByText("Next →"));
    fireEvent.click(screen.getByText("Next →")); // skip Q2
    type("3");
    fireEvent.click(screen.getByRole("button", { name: /Question 10, blank/ }));

    fireEvent.click(screen.getByText("Finish ✅"));
    expect(screen.getByText(/still have 8 blank questions/)).toBeInTheDocument();

    fireEvent.click(screen.getByText("Keep going 💪"));
    expect(onFinish).not.toHaveBeenCalled();
    expect(screen.getByText("Question 2 of 10")).toBeInTheDocument();
  });

  it("counts the current typed draft as answered in the blank check", async () => {
    const onFinish = vi.fn();
    render(<QuizScreen questions={questions} onFinish={onFinish} />);

    fireEvent.click(screen.getByRole("button", { name: /Question 10, blank/ }));
    type("99"); // typed but not navigated away
    fireEvent.click(screen.getByText("Finish ✅"));

    // 9 blanks (Q10's draft counts), not 10.
    expect(screen.getByText(/still have 9 blank questions/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Finish anyway ✅"));
    const [answers] = onFinish.mock.calls[0];
    expect(answers[9]).toBe("99");
  });
});

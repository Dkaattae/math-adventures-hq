import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import SetupScreen from "@/components/SetupScreen";
import * as api from "@/lib/api";

// The Start button is always on screen — disabled until the form is
// complete, with a nudge naming what's left (PROJECT_PLAN §3.3).

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

const start = () => screen.getByRole("button", { name: /Start Practice/ });

describe("SetupScreen start button", () => {
  beforeEach(() => {
    // No history: keep suggestions from pre-selecting anything.
    vi.spyOn(api, "getSuggestedLevel").mockResolvedValue(null);
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows Start from the beginning, disabled, listing everything missing", () => {
    render(<SetupScreen username="Kid" onStart={vi.fn()} onShowProgress={vi.fn()} />);

    expect(start()).toBeInTheDocument();
    expect(start()).toBeDisabled();
    expect(screen.getByText(/Still to pick: a grade, a topic and how tough/)).toBeInTheDocument();
  });

  it("narrows the nudge as choices are made", () => {
    render(<SetupScreen username="Kid" onStart={vi.fn()} onShowProgress={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "3" }));
    expect(screen.getByText(/Still to pick: a topic and how tough/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Addition/ }));
    expect(screen.getByText(/Pick how tough to get started/)).toBeInTheDocument();
  });

  it("does not call onStart while incomplete", () => {
    const onStart = vi.fn();
    render(<SetupScreen username="Kid" onStart={onStart} onShowProgress={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "3" }));
    fireEvent.click(start());
    expect(onStart).not.toHaveBeenCalled();
  });

  it("enables Start and swaps the nudge for encouragement once complete", () => {
    const onStart = vi.fn();
    render(<SetupScreen username="Kid" onStart={onStart} onShowProgress={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "3" }));
    fireEvent.click(screen.getByRole("button", { name: /Addition/ }));
    fireEvent.click(screen.getByRole("button", { name: /Easy/ }));

    expect(start()).toBeEnabled();
    expect(screen.queryByText(/Still to pick|to get started/)).toBeNull();

    fireEvent.click(start());
    expect(onStart).toHaveBeenCalledWith("3", "addition", "easy", "typing");
  });
});

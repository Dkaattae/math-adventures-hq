import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import SetupScreen from "@/components/SetupScreen";
import * as api from "@/lib/api";

// framer-motion is not essential here; render its elements as plain tags.
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

describe("SetupScreen grade gating", () => {
  beforeEach(() => {
    // No history → no pre-selected level, so tests start from a blank slate.
    vi.spyOn(api, "getSuggestedLevel").mockResolvedValue(null);
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("hides locked topics once Kindergarten is selected", () => {
    render(<SetupScreen username="Kid" onStart={vi.fn()} onShowProgress={vi.fn()} />);
    // Before choosing a grade every topic shows.
    expect(screen.getByRole("button", { name: /Division/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "K" }));

    expect(screen.queryByRole("button", { name: /Division/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Percentages/ })).toBeNull();
    expect(screen.getByRole("button", { name: /Addition/ })).toBeInTheDocument();
    expect(screen.getByText(/More topics unlock/)).toBeInTheDocument();
  });

  it("shows every topic at Grade 5 with no unlock hint", () => {
    render(<SetupScreen username="Kid" onStart={vi.fn()} onShowProgress={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "5" }));

    expect(screen.getByRole("button", { name: /Division/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Percentages/ })).toBeInTheDocument();
    expect(screen.queryByText(/More topics unlock/)).toBeNull();
  });

  it("clears a selected topic that the newly chosen grade doesn't offer", () => {
    const onStart = vi.fn();
    render(<SetupScreen username="Kid" onStart={onStart} onShowProgress={vi.fn()} />);

    // Pick Grade 5 + Division + Easy, then drop to Kindergarten.
    fireEvent.click(screen.getByRole("button", { name: "5" }));
    fireEvent.click(screen.getByRole("button", { name: /Division/ }));
    fireEvent.click(screen.getByRole("button", { name: /Easy/ }));
    fireEvent.click(screen.getByRole("button", { name: "K" }));

    // Division is gone and the start button shouldn't appear (no topic chosen).
    expect(screen.queryByRole("button", { name: /Division/ })).toBeNull();
    expect(screen.queryByText(/Start Practice/)).toBeNull();
  });
});

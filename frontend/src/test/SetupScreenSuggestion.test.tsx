import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import SetupScreen from "@/components/SetupScreen";
import * as api from "@/lib/api";
import type { SuggestedLevel } from "@/lib/api";

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

const isSelected = (name: string | RegExp) =>
  (screen.getByRole("button", { name }) as HTMLButtonElement).className.includes("bg-primary");

function renderSetup() {
  return render(<SetupScreen username="Kid" onStart={vi.fn()} onShowProgress={vi.fn()} />);
}

describe("SetupScreen per-topic suggestions", () => {
  let spy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    spy = vi.spyOn(api, "getSuggestedLevel");
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("re-suggests the level for the picked topic", async () => {
    spy.mockImplementation(async (_u: string, mathType?: string) =>
      mathType === "fractions"
        ? ({ grade: "2", difficulty: "easy", basedOn: 3, mathType: "fractions" } as SuggestedLevel)
        : null,
    );
    renderSetup();

    fireEvent.click(screen.getByRole("button", { name: /Fractions/ }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith("Kid", "fractions"));
    await waitFor(() => expect(isSelected("2")).toBe(true));
    expect(isSelected(/Easy/)).toBe(true);
    expect(screen.getByText(/picked up where you left off/)).toBeInTheDocument();
  });

  it("never overrides a manually chosen grade", async () => {
    spy.mockImplementation(async (_u: string, mathType?: string) =>
      mathType
        ? ({ grade: "5", difficulty: "hard", basedOn: 2, mathType } as SuggestedLevel)
        : null,
    );
    renderSetup();

    // Kid picks grade 3 by hand, then a topic with grade-5 history.
    fireEvent.click(screen.getByRole("button", { name: "3" }));
    fireEvent.click(screen.getByRole("button", { name: /Addition/ }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith("Kid", "addition"));
    // Manual grade stands; suggested difficulty still applies.
    await waitFor(() => expect(isSelected(/Hard/)).toBe(true));
    expect(isSelected("3")).toBe(true);
    expect(isSelected("5")).toBe(false);
  });

  it("shows the fresh-topic hint when the topic was never played", async () => {
    spy.mockImplementation(async (_u: string, mathType?: string) =>
      mathType === "geometry"
        ? ({ grade: "4", difficulty: "easy", basedOn: 0, mathType: "geometry" } as SuggestedLevel)
        : null,
    );
    renderSetup();

    fireEvent.click(screen.getByRole("button", { name: /Geometry/ }));

    await waitFor(() =>
      expect(screen.getByText(/First time with this topic/)).toBeInTheDocument(),
    );
    expect(isSelected("4")).toBe(true);
    expect(isSelected(/Easy/)).toBe(true);
  });
});

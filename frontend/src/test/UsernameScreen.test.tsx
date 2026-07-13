import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import UsernameScreen from "@/components/UsernameScreen";

vi.mock("@/components/Leaderboard", () => ({ default: () => null }));

function jsonResponse(body: unknown, status: number) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  } as Response;
}

describe("UsernameScreen", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("lets a returning player continue with an existing name (409)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      jsonResponse({ detail: { code: "username_taken", message: "taken" } }, 409),
    ));
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    fireEvent.change(screen.getByPlaceholderText("Type your name here..."), {
      target: { value: "Emma" },
    });
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Emma"));
  });

  it("proceeds for a brand-new name (201)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      jsonResponse({ username: "Zoe", createdAt: "2026-01-01T00:00:00Z" }, 201),
    ));
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    fireEvent.change(screen.getByPlaceholderText("Type your name here..."), {
      target: { value: "Zoe" },
    });
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Zoe"));
  });

  it("shows an error when the server is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    fireEvent.change(screen.getByPlaceholderText("Type your name here..."), {
      target: { value: "Ana" },
    });
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    await waitFor(() =>
      expect(screen.getByText(/Couldn't reach the server/)).toBeInTheDocument(),
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

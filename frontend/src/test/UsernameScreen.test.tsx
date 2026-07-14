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

/** Route the fetch mock by URL: availability checks vs. user creation. */
function stubApi({ available, createStatus }: { available: boolean; createStatus: number }) {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (String(url).includes("/api/users/check")) {
      return Promise.resolve(jsonResponse({ username: "x", available }, 200));
    }
    if (createStatus === 409) {
      return Promise.resolve(
        jsonResponse({ detail: { code: "username_taken", message: "taken" } }, 409),
      );
    }
    return Promise.resolve(
      jsonResponse({ username: "x", createdAt: "2026-01-01T00:00:00Z" }, createStatus),
    );
  }));
}

function typeName(value: string) {
  fireEvent.change(screen.getByPlaceholderText("Type your name here..."), {
    target: { value },
  });
}

describe("UsernameScreen", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("lets a returning player continue with an existing name (409)", async () => {
    stubApi({ available: false, createStatus: 409 });
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Emma");
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Emma"));
  });

  it("proceeds for a brand-new name (201)", async () => {
    stubApi({ available: true, createStatus: 201 });
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Zoe");
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Zoe"));
  });

  it("shows a welcome-back hint while typing an existing name", async () => {
    stubApi({ available: false, createStatus: 201 });
    render(<UsernameScreen onSubmit={vi.fn()} />);

    typeName("Emma");
    await waitFor(
      () => expect(screen.getByText(/Welcome back, Emma!/)).toBeInTheDocument(),
      { timeout: 2000 },
    );
  });

  it("shows a new-player hint while typing an unused name", async () => {
    stubApi({ available: true, createStatus: 201 });
    render(<UsernameScreen onSubmit={vi.fn()} />);

    typeName("Zoe");
    await waitFor(
      () => expect(screen.getByText(/New player/)).toBeInTheDocument(),
      { timeout: 2000 },
    );
  });

  it("shows an error when the server is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Ana");
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    await waitFor(() =>
      expect(screen.getByText(/Couldn't reach the server/)).toBeInTheDocument(),
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

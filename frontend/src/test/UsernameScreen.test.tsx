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

/** Route the fetch mock by URL: availability, creation, login. */
function stubApi(opts: { available: boolean; createStatus?: number; loginStatus?: number }) {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    const u = String(url);
    if (u.includes("/api/users/check")) {
      return Promise.resolve(jsonResponse({ username: "x", available: opts.available }, 200));
    }
    if (u.includes("/api/users/login")) {
      const s = opts.loginStatus ?? 200;
      return Promise.resolve(
        s === 200
          ? jsonResponse({ username: "x", createdAt: "2026-01-01T00:00:00Z" }, 200)
          : jsonResponse({ detail: { code: "invalid_login", message: "nope" } }, s),
      );
    }
    // create
    const s = opts.createStatus ?? 201;
    return Promise.resolve(
      s === 201
        ? jsonResponse({ username: "x", createdAt: "2026-01-01T00:00:00Z" }, 201)
        : jsonResponse({ detail: { code: "username_taken", message: "taken" } }, s),
    );
  }));
}

const typeName = (value: string) =>
  fireEvent.change(screen.getByPlaceholderText("Type your name here..."), { target: { value } });
const typePin = (value: string) =>
  fireEvent.change(screen.getByPlaceholderText("••••"), { target: { value } });

describe("UsernameScreen PIN flow", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("asks a new player to create a PIN, then signs them up", async () => {
    stubApi({ available: true, createStatus: 201 });
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Zoe");
    await waitFor(() => expect(screen.getByText(/Pick a secret 4-digit PIN/)).toBeInTheDocument());
    typePin("1234");
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Zoe"));
  });

  it("asks a returning player for their PIN and logs them in", async () => {
    stubApi({ available: false, loginStatus: 200 });
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Emma");
    await waitFor(() => expect(screen.getByText(/Welcome back, Emma/)).toBeInTheDocument());
    typePin("4321");
    fireEvent.click(screen.getByText("Log in 🔑"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Emma"));
  });

  it("shows an error on a wrong PIN and does not proceed", async () => {
    stubApi({ available: false, loginStatus: 401 });
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Emma");
    await waitFor(() => expect(screen.getByText(/Welcome back, Emma/)).toBeInTheDocument());
    typePin("0000");
    fireEvent.click(screen.getByText("Log in 🔑"));

    await waitFor(() => expect(screen.getByText(/PIN doesn't match/)).toBeInTheDocument());
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("keeps the submit button disabled until a 4-digit PIN is entered", async () => {
    stubApi({ available: true });
    render(<UsernameScreen onSubmit={vi.fn()} />);

    typeName("Zoe");
    await waitFor(() => expect(screen.getByText(/Pick a secret/)).toBeInTheDocument());
    const button = screen.getByText("Let's Go! 🚀") as HTMLButtonElement;
    expect(button).toBeDisabled();
    typePin("12");
    expect(button).toBeDisabled();
    typePin("1234");
    expect(button).not.toBeDisabled();
  });
});

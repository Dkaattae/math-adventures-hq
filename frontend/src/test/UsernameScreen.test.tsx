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

/** Route the fetch mock by URL: availability, creation, login, reset. */
function stubApi(opts: {
  available: boolean;
  createStatus?: number;
  loginStatus?: number;
  resetStatus?: number;
  loginError?: { code: string; message: string };
}) {
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    const u = String(url);
    if (u.includes("/api/users/check")) {
      return Promise.resolve(jsonResponse({ username: "x", available: opts.available }, 200));
    }
    if (u.includes("/api/users/login")) {
      const s = opts.loginStatus ?? 200;
      return Promise.resolve(
        s === 200
          ? jsonResponse({ username: "x", createdAt: "2026-01-01T00:00:00Z" }, 200)
          : jsonResponse(
              { detail: opts.loginError ?? { code: "invalid_login", message: "nope" } },
              s,
            ),
      );
    }
    if (u.includes("/api/users/reset-pin")) {
      const s = opts.resetStatus ?? 200;
      return Promise.resolve(
        s === 200
          ? jsonResponse({ username: "x", createdAt: "2026-01-01T00:00:00Z" }, 200)
          : jsonResponse({ detail: { code: "invalid_recovery_code", message: "nope" } }, s),
      );
    }
    // create
    const s = opts.createStatus ?? 201;
    return Promise.resolve(
      s === 201
        ? jsonResponse(
            { username: "x", createdAt: "2026-01-01T00:00:00Z", recoveryCode: "gold-otter-731" },
            201,
          )
        : jsonResponse({ detail: { code: "username_taken", message: "taken" } }, s),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
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

  it("signs a new player up, shows the rescue code once, then enters", async () => {
    stubApi({ available: true, createStatus: 201 });
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Zoe");
    await waitFor(() => expect(screen.getByText(/Pick a secret 4-digit PIN/)).toBeInTheDocument());
    typePin("1234");
    fireEvent.click(screen.getByText("Let's Go! 🚀"));

    // The rescue code interstitial appears before entering the app.
    await waitFor(() => expect(screen.getByText("gold-otter-731")).toBeInTheDocument());
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText(/I wrote it down/));
    expect(onSubmit).toHaveBeenCalledWith("Zoe");
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

  it("resets a forgotten PIN with the rescue code", async () => {
    const fetchMock = stubApi({ available: false, resetStatus: 200 });
    const onSubmit = vi.fn();
    render(<UsernameScreen onSubmit={onSubmit} />);

    typeName("Emma");
    await waitFor(() => expect(screen.getByText("Forgot your PIN?")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Forgot your PIN?"));

    fireEvent.change(screen.getByPlaceholderText("gold-otter-731"), {
      target: { value: "gold-otter-731" },
    });
    typePin("9876");
    fireEvent.click(screen.getByText("Set new PIN 🔧"));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("Emma"));
    const resetCall = fetchMock.mock.calls.find(([u]) => String(u).includes("reset-pin"));
    expect(JSON.parse(resetCall![1].body as string)).toEqual({
      username: "Emma",
      recoveryCode: "gold-otter-731",
      newPin: "9876",
    });
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

  it("surfaces the server's lockout message on a 429", async () => {
    stubApi({
      available: false,
      loginStatus: 429,
      loginError: { code: "too_many_attempts", message: "Too many tries! Take a break." },
    });
    render(<UsernameScreen onSubmit={vi.fn()} />);

    typeName("Emma");
    await waitFor(() => expect(screen.getByText(/Welcome back, Emma/)).toBeInTheDocument());
    typePin("0000");
    fireEvent.click(screen.getByText("Log in 🔑"));

    await waitFor(() => expect(screen.getByText(/Too many tries/)).toBeInTheDocument());
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

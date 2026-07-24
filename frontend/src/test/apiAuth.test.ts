import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createUser,
  getAuthToken,
  getLeaderboard,
  getUserStats,
  login,
  resetPin,
  setAuthToken,
} from "@/lib/api";

// The session token lets a player read their own progress
// (PROJECT_PLAN §2.1). The client has to remember it after login and
// attach it to later calls.

const jsonResponse = (body: unknown) =>
  ({ ok: true, status: 200, json: async () => body }) as Response;

const headersOf = (call: unknown[]) =>
  ((call[1] as RequestInit).headers ?? {}) as Record<string, string>;

describe("api session token", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setAuthToken(null);
    fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    setAuthToken(null);
    vi.unstubAllGlobals();
  });

  it("sends no Authorization header before logging in", async () => {
    await getLeaderboard();
    expect(headersOf(fetchMock.mock.calls[0]).Authorization).toBeUndefined();
  });

  it.each([
    ["signup", () => createUser("Ada", "1234"), "tok-signup"],
    ["login", () => login("Ada", "1234"), "tok-login"],
    ["PIN reset", () => resetPin("Ada", "gold-otter-731", "5678"), "tok-reset"],
  ])("stores the token issued at %s", async (_label, call, token) => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ username: "Ada", createdAt: "2026-01-01T00:00:00Z", token }),
    );
    await call();
    expect(getAuthToken()).toBe(token);
  });

  it("attaches the stored token to later requests", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ username: "Ada", createdAt: "2026-01-01T00:00:00Z", token: "tok-123" }),
    );
    await login("Ada", "1234");
    await getUserStats("Ada");

    expect(headersOf(fetchMock.mock.calls[1]).Authorization).toBe("Bearer tok-123");
  });

  it("stops sending the token once it's cleared (logout)", async () => {
    setAuthToken("tok-123");
    setAuthToken(null);
    await getUserStats("Ada");
    expect(headersOf(fetchMock.mock.calls[0]).Authorization).toBeUndefined();
  });
});

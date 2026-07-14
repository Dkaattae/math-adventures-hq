import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, checkUsername, createQuiz, createUser, getLeaderboard, submitQuiz } from "@/lib/api";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  } as Response;
}

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("createUser posts to /api/users and returns the created user", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ username: "Emma", createdAt: "2026-01-01T00:00:00Z" }, 201));
    vi.stubGlobal("fetch", fetchMock);

    const user = await createUser("Emma");

    expect(fetchMock).toHaveBeenCalledWith("/api/users", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ username: "Emma" }),
    }));
    expect(user.username).toBe("Emma");
  });

  it("throws an ApiError with the backend's code/message on a 409", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ detail: { code: "username_taken", message: "Username 'Emma' is already taken." } }, 409),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(createUser("Emma")).rejects.toMatchObject({
      status: 409,
      code: "username_taken",
    } satisfies Partial<ApiError>);
  });

  it("createQuiz posts grade/mathType/difficulty and returns the quiz with questions", async () => {
    const quiz = {
      id: "quiz-1", username: "Emma", grade: "3", mathType: "fractions", difficulty: "hard",
      questions: Array.from({ length: 10 }, (_, i) => ({ id: i, question: `Q${i}` })),
      createdAt: "2026-01-01T00:00:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(quiz, 201));
    vi.stubGlobal("fetch", fetchMock);

    const result = await createQuiz({ username: "Emma", grade: "3", mathType: "fractions", difficulty: "hard" });

    expect(result.questions).toHaveLength(10);
    expect(fetchMock).toHaveBeenCalledWith("/api/quizzes", expect.objectContaining({ method: "POST" }));
  });

  it("submitQuiz posts answers to /api/quizzes/{id}/submit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      quizId: "quiz-1", username: "Emma", score: 9, total: 10, timeUsedSeconds: 90,
      badge: "🥈", results: [], submittedAt: "2026-01-01T00:00:00Z",
    }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await submitQuiz("quiz-1", { answers: Array(10).fill("1"), timeUsedSeconds: 90 });

    expect(fetchMock).toHaveBeenCalledWith("/api/quizzes/quiz-1/submit", expect.objectContaining({ method: "POST" }));
    expect(result.score).toBe(9);
  });

  it("checkUsername queries availability with the name URL-encoded", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ username: "Mia B", available: true }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await checkUsername("Mia B");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/users/check?username=Mia+B");
    expect(result.available).toBe(true);
  });

  it("getLeaderboard builds query params only for provided filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await getLeaderboard({ mathType: "geometry", limit: 5 });

    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("mathType=geometry");
    expect(calledUrl).toContain("limit=5");
    expect(calledUrl).not.toContain("difficulty");
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProgressScreen from "@/components/ProgressScreen";
import * as api from "@/lib/api";
import type { UserStats } from "@/lib/api";

function renderProgress(username = "Ada") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ProgressScreen username={username} onBack={() => {}} />
    </QueryClientProvider>,
  );
}

const stats: UserStats = {
  username: "Ada",
  totalQuizzes: 3,
  averageScore: 8,
  bestScore: 10,
  byTopic: [
    { mathType: "addition", quizzes: 2, averageScore: 8, bestScore: 10 },
    { mathType: "geometry", quizzes: 1, averageScore: 8, bestScore: 8 },
  ],
  recent: [
    { mathType: "addition", grade: "2", difficulty: "easy", score: 10, total: 10, time: "1m 00s", achievedAt: "2026-01-03T00:00:00Z" },
    { mathType: "geometry", grade: "2", difficulty: "easy", score: 8, total: 10, time: "1m 20s", achievedAt: "2026-01-02T00:00:00Z" },
  ],
};

describe("ProgressScreen", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows headline stats and per-topic breakdown", async () => {
    vi.spyOn(api, "getUserStats").mockResolvedValue(stats);
    renderProgress();

    await waitFor(() => expect(screen.getByText("📊 Ada's Progress")).toBeInTheDocument());
    // headline stat tiles
    expect(screen.getByText("Quizzes")).toBeInTheDocument();
    expect(screen.getByText("Best")).toBeInTheDocument();
    expect(screen.getByText("Average")).toBeInTheDocument();
    // Addition/Geometry appear in both the by-topic and recent sections.
    expect(screen.getAllByText("Addition").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("By topic")).toBeInTheDocument();
    expect(screen.getByText("Recent quizzes")).toBeInTheDocument();
    expect(screen.getByText("2 quizzes")).toBeInTheDocument();
    expect(screen.getByText("best 10/10")).toBeInTheDocument();
  });

  it("shows an empty state for a player with no quizzes", async () => {
    vi.spyOn(api, "getUserStats").mockResolvedValue({
      username: "New", totalQuizzes: 0, averageScore: 0, bestScore: 0, byTopic: [], recent: [],
    });
    renderProgress("New");

    await waitFor(() => expect(screen.getByText(/No quizzes yet/)).toBeInTheDocument());
  });
});

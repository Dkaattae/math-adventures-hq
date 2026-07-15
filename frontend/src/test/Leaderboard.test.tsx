import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Leaderboard from "@/components/Leaderboard";
import * as api from "@/lib/api";

function renderLeaderboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Leaderboard />
    </QueryClientProvider>,
  );
}

const sampleEntry = {
  name: "Emma",
  score: 10,
  total: 10,
  timeUsedSeconds: 80,
  time: "1m 20s",
  badge: "🏆",
  achievedAt: "2026-01-01T00:00:00Z",
};

describe("Leaderboard filters", () => {
  beforeEach(() => {
    vi.spyOn(api, "getLeaderboard").mockResolvedValue([sampleEntry] as never);
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("fetches the global top scores on mount (no filters)", async () => {
    renderLeaderboard();
    await waitFor(() => expect(screen.getByText("Emma")).toBeInTheDocument());
    expect(api.getLeaderboard).toHaveBeenCalledWith(
      expect.objectContaining({ grade: undefined, mathType: undefined, difficulty: undefined }),
    );
  });

  it("refetches with the chosen grade and topic filters", async () => {
    renderLeaderboard();
    await waitFor(() => expect(screen.getByText("Emma")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Grade"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "fractions" } });

    await waitFor(() =>
      expect(api.getLeaderboard).toHaveBeenCalledWith(
        expect.objectContaining({ grade: "3", mathType: "fractions" }),
      ),
    );
  });

  it("shows a friendly empty state when no scores match", async () => {
    vi.spyOn(api, "getLeaderboard").mockResolvedValue([] as never);
    renderLeaderboard();
    await waitFor(() =>
      expect(screen.getByText(/No scores here yet/)).toBeInTheDocument(),
    );
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

// PROJECT_PLAN §3.1: unfiltered, "10/10 — 1m 20s" says nothing about
// whether it was K easy or grade 5 hard, which made the whole board look
// like one race. Each row now carries the level it was set at.
describe("Leaderboard row context", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // Scoped to the row: the filter dropdowns hold "Hard" and "Grade 3"
  // too, and a document-wide query would pass on those alone.
  const row = async () => {
    await waitFor(() => expect(screen.getByText("Emma")).toBeInTheDocument());
    return within(screen.getAllByRole("listitem")[0]);
  };

  it("labels each row with its grade, topic and difficulty", async () => {
    vi.spyOn(api, "getLeaderboard").mockResolvedValue([
      { ...sampleEntry, grade: "3", mathType: "fractions", difficulty: "hard" },
    ] as never);
    renderLeaderboard();

    const r = await row();
    expect(r.getByText("G3")).toBeInTheDocument();
    expect(r.getByText(/Fractions/)).toBeInTheDocument();
    expect(r.getByText("Hard")).toBeInTheDocument();
  });

  it("writes kindergarten as K, not G K", async () => {
    vi.spyOn(api, "getLeaderboard").mockResolvedValue([
      { ...sampleEntry, grade: "K", mathType: "addition", difficulty: "easy" },
    ] as never);
    renderLeaderboard();

    const r = await row();
    expect(r.getByText("K")).toBeInTheDocument();
    expect(r.queryByText("GK")).toBeNull();
  });

  it("leaves rows from before these columns existed unlabelled", async () => {
    vi.spyOn(api, "getLeaderboard").mockResolvedValue([sampleEntry] as never);
    renderLeaderboard();

    const r = await row();
    expect(r.queryByText("Hard")).toBeNull();
    expect(r.queryByText(/^G\d$/)).toBeNull();
  });
});

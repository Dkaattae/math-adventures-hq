import { describe, expect, it } from "vitest";
import { recommendationText, type ServerRecommendation } from "@/data/quizConfig";

const current = { grade: "3", difficulty: "easy" } as const;

describe("recommendationText (renders the server's level decision)", () => {
  it("celebrates a level-up to a new difficulty with a CTA", () => {
    const server: ServerRecommendation = { direction: "up", grade: "3", difficulty: "medium" };
    const r = recommendationText(current, server, 9);
    expect(r.grade).toBe("3");
    expect(r.difficulty).toBe("medium");
    expect(r.cta).toContain("medium mode");
    expect(r.headline).toMatch(/fire/i);
  });

  it("names the next grade when moving up a grade", () => {
    const server: ServerRecommendation = { direction: "up", grade: "4", difficulty: "easy" };
    const r = recommendationText({ grade: "3", difficulty: "hard" }, server, 10);
    expect(r.cta).toContain("Grade 4");
  });

  it("shows mastery (no CTA) when the server holds at the top", () => {
    const server: ServerRecommendation = { direction: "up", grade: "5", difficulty: "hard" };
    const r = recommendationText({ grade: "5", difficulty: "hard" }, server, 10);
    expect(r.cta).toBeNull();
    expect(r.headline).toMatch(/legend/i);
  });

  it("offers a gentler level on a down decision", () => {
    const server: ServerRecommendation = { direction: "down", grade: "4", difficulty: "medium" };
    const r = recommendationText({ grade: "4", difficulty: "hard" }, server, 3);
    expect(r.difficulty).toBe("medium");
    expect(r.cta).toContain("medium mode");
  });

  it("encourages a retry when down but already at the floor", () => {
    const server: ServerRecommendation = { direction: "down", grade: "K", difficulty: "easy" };
    const r = recommendationText({ grade: "K", difficulty: "easy" }, server, 1);
    expect(r.cta).toBe("Try again →");
    expect(r.detail).toContain("Kindergarten");
  });

  it("suggests steady practice at the same level for a middling score", () => {
    const server: ServerRecommendation = { direction: "steady", grade: "2", difficulty: "medium" };
    const r = recommendationText({ grade: "2", difficulty: "medium" }, server, 6);
    expect(r.cta).toBe("Practice again →");
  });
});

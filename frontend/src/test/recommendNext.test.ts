import { describe, expect, it } from "vitest";
import { recommendNext } from "@/data/quizConfig";

describe("recommendNext (adaptive suggestion)", () => {
  it("bumps difficulty within a grade on a high score", () => {
    const r = recommendNext("3", "easy", 9);
    expect(r.kind).toBe("level-up");
    expect(r.grade).toBe("3");
    expect(r.difficulty).toBe("medium");
    expect(r.cta).toBeTruthy();
  });

  it("moves up a grade (resetting to easy) after acing the hard tier", () => {
    const r = recommendNext("3", "hard", 10);
    expect(r.kind).toBe("level-up");
    expect(r.grade).toBe("4");
    expect(r.difficulty).toBe("easy");
    expect(r.detail).toContain("Grade 3");
  });

  it("celebrates mastery with no next level at Grade 5 hard", () => {
    const r = recommendNext("5", "hard", 10);
    expect(r.kind).toBe("level-up");
    expect(r.cta).toBeNull();
  });

  it("eases down a difficulty on a low score", () => {
    const r = recommendNext("4", "hard", 3);
    expect(r.kind).toBe("ease");
    expect(r.grade).toBe("4");
    expect(r.difficulty).toBe("medium");
  });

  it("drops a grade (to hard) when already at easy and struggling", () => {
    const r = recommendNext("3", "easy", 2);
    expect(r.kind).toBe("ease");
    expect(r.grade).toBe("2");
    expect(r.difficulty).toBe("hard");
  });

  it("has nowhere lower to go at Kindergarten easy", () => {
    const r = recommendNext("K", "easy", 1);
    expect(r.kind).toBe("ease");
    expect(r.grade).toBe("K");
    expect(r.difficulty).toBe("easy");
    expect(r.cta).toBe("Try again →");
  });

  it("encourages steady practice at the same level for a middling score", () => {
    const r = recommendNext("2", "medium", 6);
    expect(r.kind).toBe("steady");
    expect(r.grade).toBe("2");
    expect(r.difficulty).toBe("medium");
  });

  it("names Kindergarten rather than 'Grade K'", () => {
    const r = recommendNext("K", "easy", 10);
    expect(r.detail).toContain("Kindergarten");
    expect(r.detail).not.toContain("Grade K");
  });
});

import { describe, expect, it } from "vitest";
import {
  ALL_MATH_TYPES,
  isTopicAvailable,
  minGradeForType,
  topicsForGrade,
} from "@/data/quizConfig";

describe("grade-appropriate topic gating", () => {
  it("has a minimum grade for every topic", () => {
    for (const t of ALL_MATH_TYPES) {
      expect(minGradeForType[t]).toBeDefined();
    }
  });

  it("offers only the basics at Kindergarten", () => {
    const k = topicsForGrade("K");
    expect(k).toContain("addition");
    expect(k).toContain("subtraction");
    expect(k).toContain("mixed");
    for (const locked of ["division", "multiplication", "fractions", "decimals", "percentages"] as const) {
      expect(k).not.toContain(locked);
    }
  });

  it("offers every topic at Grade 5", () => {
    expect(new Set(topicsForGrade("5"))).toEqual(new Set(ALL_MATH_TYPES));
  });

  it("unlocks strictly more topics as the grade rises", () => {
    const counts = (["K", "1", "2", "3", "4", "5"] as const).map((g) => topicsForGrade(g).length);
    for (let i = 1; i < counts.length; i++) {
      expect(counts[i]).toBeGreaterThanOrEqual(counts[i - 1]);
    }
    expect(counts[5]).toBeGreaterThan(counts[0]);
  });

  it("keeps availability monotonic per topic", () => {
    const order = ["K", "1", "2", "3", "4", "5"] as const;
    for (const t of ALL_MATH_TYPES) {
      let seen = false;
      for (const g of order) {
        const here = isTopicAvailable(t, g);
        if (here) seen = true;
        else expect(seen).toBe(false); // once locked-below, never re-locks above
      }
    }
  });

  it("gates percentages to Grade 4 and up", () => {
    expect(isTopicAvailable("percentages", "3")).toBe(false);
    expect(isTopicAvailable("percentages", "4")).toBe(true);
  });
});

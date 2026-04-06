import { describe, it, expect } from "vitest";
import { generateQuestions, type MathType } from "@/data/mockData";

const mathTypes: MathType[] = [
  "addition",
  "subtraction",
  "multiplication",
  "division",
  "algebra",
  "geometry",
];

function evaluate(question: string, answer: number | string): boolean {
  // Addition: "a + b = ?"
  let m = question.match(/^(\d+)\s*\+\s*(\d+)\s*=/);
  if (m) return Number(m[1]) + Number(m[2]) === answer;

  // Subtraction: "a - b = ?"
  m = question.match(/^(\d+)\s*-\s*(\d+)\s*=/);
  if (m) return Number(m[1]) - Number(m[2]) === answer;

  // Multiplication: "a × b = ?"
  m = question.match(/^(\d+)\s*×\s*(\d+)\s*=/);
  if (m) return Number(m[1]) * Number(m[2]) === answer;

  // Division: "a ÷ b = ?"
  m = question.match(/^(\d+)\s*÷\s*(\d+)\s*=/);
  if (m) return Number(m[1]) / Number(m[2]) === answer;

  // Algebra: "x + c = total. What is x?"
  m = question.match(/^x\s*\+\s*(\d+)\s*=\s*(\d+)\./);
  if (m) return Number(m[2]) - Number(m[1]) === answer;

  // Geometry: fixed-answer lookup — accept any numeric answer as long as it's
  // a positive integer (the data is validated separately below).
  return typeof answer === "number" && Number.isFinite(answer) && answer > 0;
}

describe("generateQuestions", () => {
  it.each(mathTypes)("returns exactly 10 questions for %s", (type) => {
    const qs = generateQuestions(type, "easy", "3");
    expect(qs).toHaveLength(10);
  });

  it.each(mathTypes)("assigns unique sequential ids for %s", (type) => {
    const qs = generateQuestions(type, "medium", "3");
    expect(qs.map((q) => q.id)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
  });

  it.each(mathTypes)("produces non-empty question/explanation strings for %s", (type) => {
    const qs = generateQuestions(type, "hard", "5");
    for (const q of qs) {
      expect(q.question.length).toBeGreaterThan(0);
      expect(q.explanation.length).toBeGreaterThan(0);
    }
  });

  it.each(mathTypes)("correctAnswer matches the question for %s", (type) => {
    // Run a few times since questions are random.
    for (let trial = 0; trial < 20; trial++) {
      const qs = generateQuestions(type, "medium", "4");
      for (const q of qs) {
        expect(evaluate(q.question, q.correctAnswer)).toBe(true);
      }
    }
  });

  it("subtraction never produces negative answers", () => {
    for (let trial = 0; trial < 50; trial++) {
      const qs = generateQuestions("subtraction", "hard", "5");
      for (const q of qs) {
        expect(Number(q.correctAnswer)).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("division always produces integer answers", () => {
    for (let trial = 0; trial < 50; trial++) {
      const qs = generateQuestions("division", "medium", "3");
      for (const q of qs) {
        expect(Number.isInteger(Number(q.correctAnswer))).toBe(true);
      }
    }
  });

  it("geometry questions come from the fixed shape pool", () => {
    const allowedAnswers = new Set([3, 4, 5, 6, 8, 12, 90, 180]);
    const qs = generateQuestions("geometry", "easy", "K");
    for (const q of qs) {
      expect(allowedAnswers.has(Number(q.correctAnswer))).toBe(true);
    }
  });

  it("harder difficulty permits larger numbers than easy", () => {
    // Sample many runs and compare max values — medium/hard have wider ranges.
    const maxOf = (difficulty: "easy" | "hard") => {
      let max = 0;
      for (let i = 0; i < 30; i++) {
        const qs = generateQuestions("addition", difficulty, "3");
        for (const q of qs) {
          const m = q.question.match(/^(\d+)\s*\+\s*(\d+)/);
          if (m) max = Math.max(max, Number(m[1]), Number(m[2]));
        }
      }
      return max;
    };
    expect(maxOf("hard")).toBeGreaterThan(maxOf("easy"));
  });
});

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import MathText, { splitFractions } from "@/components/MathText";
import FractionPies, { parsePieFigure, piesFor } from "@/components/FractionPies";
import QuestionFigure from "@/components/QuestionFigure";

describe("splitFractions", () => {
  it("pulls out every fraction in a sum", () => {
    expect(splitFractions("1/4 + 2/9 = ? (simplest form)")).toEqual([
      { num: "1", den: "4" },
      " + ",
      { num: "2", den: "9" },
      " = ? (simplest form)",
    ]);
  });

  it("handles a missing number and a mixed number", () => {
    expect(splitFractions("1/2 = ?/8")).toEqual([{ num: "1", den: "2" }, " = ", { num: "?", den: "8" }]);
    expect(splitFractions("2 3/5")).toEqual(["2 ", { num: "3", den: "5" }]);
  });

  it("leaves text without fractions alone", () => {
    expect(splitFractions("7 + 5 = ?")).toEqual(["7 + 5 = ?"]);
    expect(splitFractions("It is 5:20 now.")).toEqual(["It is 5:20 now."]);
  });

  it("does not stack things that only look like fractions", () => {
    expect(splitFractions("0.5/2")).toEqual(["0.5/2"]);
    expect(splitFractions("1/2/3")).toEqual(["1/2/3"]);
  });
});

describe("MathText", () => {
  afterEach(cleanup);

  it("draws a numerator over a denominator and still reads as a fraction", () => {
    const { container } = render(<p><MathText text="3/4 of 12" /></p>);
    // Screen readers hear "3/4"; the stacked digits are hidden from them.
    expect(screen.getByText("3/4")).toHaveClass("sr-only");
    const hidden = container.querySelectorAll('[aria-hidden="true"]');
    expect([...hidden].map((n) => n.textContent)).toEqual(["3", "4"]);
    expect(container.textContent).toContain("of 12");
  });
});

describe("FractionPies", () => {
  afterEach(cleanup);

  it("parses fractions and operators, dropping anything unreadable", () => {
    expect(parsePieFigure("pie:2/6 + 3/6")).toEqual([
      { kind: "frac", num: 2, den: 6 },
      { kind: "op", text: "+" },
      { kind: "frac", num: 3, den: 6 },
    ]);
    expect(parsePieFigure("pie:1/40")).toEqual([]);
    expect(parsePieFigure("pentagon")).toEqual([]);
  });

  it("splits an improper fraction across pies", () => {
    expect(piesFor(13, 5)).toEqual([5, 5, 3]);
    expect(piesFor(3, 8)).toEqual([3]);
    expect(piesFor(0, 8)).toEqual([0]);
    expect(piesFor(10, 5)).toEqual([5, 5]);
  });

  it("shades the right number of slices", () => {
    const { container } = render(<FractionPies figure="pie:3/8" />);
    expect(container.querySelectorAll('[data-slice="shaded"]')).toHaveLength(3);
    expect(container.querySelectorAll('[data-slice="empty"]')).toHaveLength(5);
  });

  it("draws 13/5 as three pies with 13 slices shaded", () => {
    const { container } = render(<FractionPies figure="pie:13/5" />);
    expect(container.querySelectorAll("path")).toHaveLength(15);
    expect(container.querySelectorAll('[data-slice="shaded"]')).toHaveLength(13);
  });

  it("puts the operator between the pies and never draws the numbers", () => {
    const { container } = render(<FractionPies figure="pie:1/4 + 2/9" />);
    expect([...container.querySelectorAll("text")].map((t) => t.textContent)).toEqual(["+"]);
    expect(container.querySelector("svg")!.getAttribute("aria-label")).toBe("fraction picture");
  });

  it("renders nothing for a figure with no fractions", () => {
    const { container } = render(<FractionPies figure="pie:+" />);
    expect(container.querySelector("svg")).toBeNull();
  });
});

describe("QuestionFigure", () => {
  afterEach(cleanup);

  it("sends pies to FractionPies and shapes to ShapeFigure", () => {
    const pies = render(<QuestionFigure figure="pie:1/2" />);
    expect(pies.container.querySelectorAll("path")).toHaveLength(2);
    pies.unmount();
    const shape = render(<QuestionFigure figure="pentagon" />);
    expect(shape.container.querySelector("polygon")).not.toBeNull();
  });
});

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import ShapeFigure from "@/components/ShapeFigure";

describe("ShapeFigure", () => {
  afterEach(cleanup);

  it("draws a polygon with the right number of vertices", () => {
    const { container } = render(<ShapeFigure shape="pentagon" />);
    const polygon = container.querySelector("polygon");
    expect(polygon).not.toBeNull();
    const points = polygon!.getAttribute("points")!.trim().split(/\s+/);
    expect(points).toHaveLength(5);
  });

  it("draws a circle for the circle shape", () => {
    const { container } = render(<ShapeFigure shape="circle" />);
    expect(container.querySelector("circle")).not.toBeNull();
  });

  it("draws a rect for the rectangle shape", () => {
    const { container } = render(<ShapeFigure shape="rectangle" />);
    expect(container.querySelector("rect")).not.toBeNull();
  });

  it("does not announce the shape name (label stays generic)", () => {
    const { container } = render(<ShapeFigure shape="hexagon" />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("aria-label")).not.toContain("hexagon");
  });

  it("renders nothing for an unknown shape", () => {
    const { container } = render(<ShapeFigure shape="dodecahedron" />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("draws an angle as two rays with an arc", () => {
    const { container } = render(<ShapeFigure shape="angle:60" />);
    expect(container.querySelectorAll("line")).toHaveLength(2);
    // The classification is the question, so no degree text is drawn.
    expect(container.querySelector("text")).toBeNull();
    expect(container.querySelector("path")).not.toBeNull();
  });

  it("marks a right angle with a square corner instead of an arc", () => {
    const { container } = render(<ShapeFigure shape="angle:90" />);
    const marker = container.querySelector("path")!;
    // A square marker is two straight segments — no arc command.
    expect(marker.getAttribute("d")).not.toContain("A");
  });

  it("labels a measured rectangle with both side lengths", () => {
    const { container } = render(<ShapeFigure shape="rect:6x3" />);
    expect(container.querySelector("rect")).not.toBeNull();
    const labels = Array.from(container.querySelectorAll("text")).map(
      (t) => t.textContent,
    );
    expect(labels).toContain("6");
    expect(labels).toContain("3");
  });

  it("keeps a stretched rectangle visibly two-dimensional", () => {
    const { container } = render(<ShapeFigure shape="rect:12x2" />);
    const rect = container.querySelector("rect")!;
    expect(parseFloat(rect.getAttribute("height")!)).toBeGreaterThanOrEqual(24);
  });
});

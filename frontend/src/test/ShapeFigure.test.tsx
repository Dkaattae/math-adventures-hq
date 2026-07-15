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
});

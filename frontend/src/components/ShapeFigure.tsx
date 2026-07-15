// Draws a named geometry shape as an inline SVG for visual questions.
// Regular polygons are computed from a side count; circle and rectangle
// are special-cased.

const POLYGON_SIDES: Record<string, number> = {
  triangle: 3,
  square: 4,
  pentagon: 5,
  hexagon: 6,
  heptagon: 7,
  octagon: 8,
};

const SIZE = 120;
const CENTER = SIZE / 2;
const RADIUS = SIZE / 2 - 10;

function polygonPoints(sides: number, rotationDeg: number): string {
  const rotation = (rotationDeg * Math.PI) / 180;
  return Array.from({ length: sides }, (_, i) => {
    const angle = rotation + (i * 2 * Math.PI) / sides;
    const x = CENTER + RADIUS * Math.cos(angle);
    const y = CENTER + RADIUS * Math.sin(angle);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

interface Props {
  shape: string;
  /** Accessible label; defaults to a generic description so the answer
   *  isn't announced (the question asks the player to identify it). */
  label?: string;
  /** Tailwind sizing for the rendered SVG. */
  className?: string;
}

const ShapeFigure = ({ shape, label = "geometry shape", className = "w-28 h-28 mx-auto" }: Props) => {
  const stroke = "hsl(var(--primary))";
  const fill = "hsl(var(--primary) / 0.12)";
  const common = { fill, stroke, strokeWidth: 4, strokeLinejoin: "round" as const };

  let figure;
  if (shape === "circle") {
    figure = <circle cx={CENTER} cy={CENTER} r={RADIUS} {...common} />;
  } else if (shape === "rectangle") {
    const w = SIZE - 20;
    const h = SIZE - 50;
    figure = <rect x={(SIZE - w) / 2} y={(SIZE - h) / 2} width={w} height={h} rx={4} {...common} />;
  } else if (shape in POLYGON_SIDES) {
    // Point the shape "up": odd polygons look best with a vertex at top.
    const sides = POLYGON_SIDES[shape];
    const rotation = shape === "square" ? 45 : -90;
    figure = <polygon points={polygonPoints(sides, rotation)} {...common} />;
  } else {
    return null;
  }

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={label}
      className={className}
    >
      {figure}
    </svg>
  );
};

export default ShapeFigure;

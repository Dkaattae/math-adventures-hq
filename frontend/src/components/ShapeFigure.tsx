// Draws a geometry figure as an inline SVG for visual questions.
// Three kinds of figure string:
//   - named shapes ("pentagon", "circle") — computed regular polygons
//     plus circle/rectangle
//   - "angle:<degrees>" — two rays with an arc (or a right-angle mark)
//   - "rect:<w>x<h>" — a rectangle with labelled side lengths, for
//     perimeter/area questions

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
  if (shape.startsWith("angle:")) {
    // An angle to classify: vertex bottom-left, one arm flat, the other
    // rotated up by the given degrees. No number is drawn — naming the
    // measure would answer "is this acute or obtuse?" for the player.
    const deg = Math.max(10, Math.min(170, parseInt(shape.slice(6), 10) || 60));
    const vx = 22;
    const vy = SIZE - 24;
    const arm = SIZE - 40;
    const rad = (deg * Math.PI) / 180;
    const x2 = vx + arm * Math.cos(rad);
    const y2 = vy - arm * Math.sin(rad);
    const lineProps = { stroke, strokeWidth: 4, strokeLinecap: "round" as const };
    let marker;
    if (deg === 90) {
      const m = 16;
      marker = (
        <path d={`M ${vx + m} ${vy} L ${vx + m} ${vy - m} L ${vx} ${vy - m}`}
              fill="none" stroke={stroke} strokeWidth={3} />
      );
    } else {
      const r = 20;
      const ax = vx + r * Math.cos(rad);
      const ay = vy - r * Math.sin(rad);
      marker = (
        <path d={`M ${vx + r} ${vy} A ${r} ${r} 0 0 0 ${ax.toFixed(1)} ${ay.toFixed(1)}`}
              fill="none" stroke={stroke} strokeWidth={3} />
      );
    }
    figure = (
      <g>
        <line x1={vx} y1={vy} x2={vx + arm} y2={vy} {...lineProps} />
        <line x1={vx} y1={vy} x2={x2.toFixed(1)} y2={y2.toFixed(1)} {...lineProps} />
        {marker}
      </g>
    );
  } else if (shape.startsWith("rect:")) {
    // A rectangle with labelled sides, e.g. "rect:6x3" — the numbers are
    // the question's data, so they ARE drawn (unitless; the question
    // text supplies the unit).
    const [wRaw, hRaw] = shape.slice(5).split("x").map((n) => parseInt(n, 10));
    const w = Math.max(1, wRaw || 4);
    const h = Math.max(1, hRaw || 3);
    // Scale the longer side to the drawing area, keep the aspect ratio
    // within sane bounds so a 12x2 strip is still visibly a rectangle.
    const maxW = SIZE - 44;
    const maxH = SIZE - 56;
    const scale = Math.min(maxW / w, maxH / h);
    const drawW = Math.max(30, w * scale);
    const drawH = Math.max(24, h * scale);
    const x = (SIZE - drawW) / 2;
    const y = (SIZE - drawH) / 2 - 4;
    const textProps = {
      fill: "hsl(var(--foreground))",
      fontSize: 13,
      fontWeight: 700,
      textAnchor: "middle" as const,
    };
    figure = (
      <g>
        <rect x={x} y={y} width={drawW} height={drawH} rx={3} {...common} />
        <text x={x + drawW / 2} y={y + drawH + 16} {...textProps}>{w}</text>
        <text x={x + drawW + 12} y={y + drawH / 2 + 5} {...textProps}>{h}</text>
      </g>
    );
  } else if (shape === "circle") {
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

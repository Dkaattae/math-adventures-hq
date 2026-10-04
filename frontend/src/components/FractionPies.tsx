// Draws the pie charts that go with a fraction question.
//
// The figure string is "pie:" followed by space-separated tokens, each a
// fraction ("3/8") or an operator ("+", "-"):
//   "pie:3/8"        one pie cut in 8, 3 slices shaded
//   "pie:2/6 + 3/6"  two pies with a plus between them
//   "pie:1/3 1/5"    two pies side by side, to compare
//   "pie:13/5"       more than a whole: two full pies and 3/5 of a third
//   "pie:0/8"        a pie cut in 8 with nothing shaded (shows the cut)
//
// No numbers are drawn — the question text has them, and for "what part
// is shaded?" the picture is the question.

const PIE = 100;
const R = 44;
const PIE_GAP = 8; // between the pies of one improper fraction
const ITEM_GAP = 24; // between two fractions with nothing in between
const OP_WIDTH = 36;
const MAX_DEN = 12;
const MAX_PIES = 3;

type Token = { kind: "frac"; num: number; den: number } | { kind: "op"; text: string };

export function parsePieFigure(figure: string): Token[] {
  if (!figure.startsWith("pie:")) return [];
  const tokens: Token[] = [];
  for (const raw of figure.slice(4).trim().split(/\s+/)) {
    const m = raw.match(/^(\d+)\/(\d+)$/);
    if (m) {
      const num = parseInt(m[1], 10);
      const den = parseInt(m[2], 10);
      // Out of range would be unreadable (or a runaway loop); skip it.
      if (den >= 1 && den <= MAX_DEN && num <= den * MAX_PIES) {
        tokens.push({ kind: "frac", num, den });
      }
    } else if (raw === "+" || raw === "-") {
      tokens.push({ kind: "op", text: raw === "-" ? "−" : "+" });
    }
  }
  return tokens;
}

/** Shaded-slice counts for each pie a fraction needs: 13/5 → [5, 5, 3]. */
export function piesFor(num: number, den: number): number[] {
  const count = Math.max(1, Math.ceil(num / den));
  return Array.from({ length: count }, (_, i) => Math.max(0, Math.min(den, num - i * den)));
}

function wedgePath(cx: number, cy: number, i: number, den: number): string {
  const a0 = -Math.PI / 2 + (i * 2 * Math.PI) / den;
  const a1 = -Math.PI / 2 + ((i + 1) * 2 * Math.PI) / den;
  const x0 = cx + R * Math.cos(a0);
  const y0 = cy + R * Math.sin(a0);
  const x1 = cx + R * Math.cos(a1);
  const y1 = cy + R * Math.sin(a1);
  return `M ${cx} ${cy} L ${x0.toFixed(2)} ${y0.toFixed(2)} A ${R} ${R} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)} Z`;
}

const shadedFill = "hsl(var(--primary))";
const emptyFill = "hsl(var(--card))";
const edge = "hsl(var(--foreground) / 0.6)";

const Pie = ({ x, den, shaded }: { x: number; den: number; shaded: number }) => {
  const cx = x + PIE / 2;
  const cy = PIE / 2;
  if (den === 1) {
    return (
      <circle cx={cx} cy={cy} r={R} fill={shaded ? shadedFill : emptyFill} stroke={edge} strokeWidth={2.5}
              data-slice={shaded ? "shaded" : "empty"} />
    );
  }
  return (
    <g>
      {Array.from({ length: den }, (_, i) => (
        <path
          key={i}
          d={wedgePath(cx, cy, i, den)}
          fill={i < shaded ? shadedFill : emptyFill}
          stroke={edge}
          strokeWidth={2}
          strokeLinejoin="round"
          data-slice={i < shaded ? "shaded" : "empty"}
        />
      ))}
      <circle cx={cx} cy={cy} r={R} fill="none" stroke={edge} strokeWidth={2.5} />
    </g>
  );
};

interface Props {
  figure: string;
  /** Tailwind sizing: set the height, the width follows the pie count. */
  className?: string;
}

const FractionPies = ({ figure, className = "h-24 md:h-28 w-auto max-w-full mx-auto" }: Props) => {
  const tokens = parsePieFigure(figure);
  if (!tokens.some((t) => t.kind === "frac")) return null;

  const drawn: JSX.Element[] = [];
  let x = 0;
  let prev: Token["kind"] | null = null;
  tokens.forEach((token, t) => {
    if (token.kind === "op") {
      drawn.push(
        <text key={`op${t}`} x={x + OP_WIDTH / 2} y={PIE / 2 + 11} textAnchor="middle"
              fontSize={32} fontWeight={700} fill="hsl(var(--foreground))">
          {token.text}
        </text>,
      );
      x += OP_WIDTH;
    } else {
      if (prev === "frac") x += ITEM_GAP;
      piesFor(token.num, token.den).forEach((shaded, p) => {
        if (p > 0) x += PIE_GAP;
        drawn.push(<Pie key={`pie${t}-${p}`} x={x} den={token.den} shaded={shaded} />);
        x += PIE;
      });
    }
    prev = token.kind;
  });

  return (
    <svg
      viewBox={`0 0 ${x} ${PIE}`}
      width={x}
      height={PIE}
      role="img"
      aria-label="fraction picture"
      className={className}
    >
      {drawn}
    </svg>
  );
};

export default FractionPies;

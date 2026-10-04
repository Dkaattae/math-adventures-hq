// Prints question text with every "a/b" stacked as a real fraction — a
// numerator over a bar over a denominator — instead of "1/4 + 2/9", which
// is hard to read on a phone. The backend keeps plain "a/b" text (it's
// also what a kid types back); only the display changes.
//
// "?" can stand in for either number ("1/2 = ?/8"), and a mixed number
// ("2 3/5") needs nothing special: the whole number is just text in
// front of a stacked fraction.

import { Fragment } from "react";

export type MathPart = string | { num: string; den: string };

// A run of digits (or "?") either side of a slash, not glued to another
// number, decimal point or slash on either side, so "0.5/2" or "1/2/3"
// stay as typed. No lookbehind: older iOS Safari can't parse it, and a
// regex syntax error there would take down the whole app.
const FRACTION = /(^|[^\d./])(\d+|\?)\/(\d+|\?)(?![\d/.])/g;

export function splitFractions(text: string): MathPart[] {
  const parts: MathPart[] = [];
  let last = 0;
  for (const m of text.matchAll(FRACTION)) {
    const start = (m.index ?? 0) + m[1].length;
    if (start > last) parts.push(text.slice(last, start));
    parts.push({ num: m[2], den: m[3] });
    last = (m.index ?? 0) + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export const StackedFraction = ({ num, den }: { num: string; den: string }) => (
  <span className="inline-flex flex-col items-center align-middle mx-[0.12em] text-[0.82em] leading-[1.1] tabular-nums">
    {/* Screen readers get "3/4"; the stacked layout is for the eyes. */}
    <span className="sr-only">{`${num}/${den}`}</span>
    <span aria-hidden="true" className="px-[0.15em]">{num}</span>
    <span aria-hidden="true" className="px-[0.15em] border-t-2 border-current w-full text-center">{den}</span>
  </span>
);

const MathText = ({ text }: { text: string }) => (
  <>
    {splitFractions(text).map((part, i) =>
      typeof part === "string" ? (
        <Fragment key={i}>{part}</Fragment>
      ) : (
        <StackedFraction key={i} num={part.num} den={part.den} />
      ),
    )}
  </>
);

export default MathText;

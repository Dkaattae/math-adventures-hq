// The picture that rides along with a question: fraction pies for a
// "pie:" figure, a geometry shape for everything else.

import FractionPies from "./FractionPies";
import ShapeFigure from "./ShapeFigure";

interface Props {
  figure: string;
  /** "large" on the quiz card, "small" in the results review list. */
  size?: "large" | "small";
}

const QuestionFigure = ({ figure, size = "large" }: Props) => {
  if (figure.startsWith("pie:")) {
    return (
      <FractionPies
        figure={figure}
        className={size === "large" ? "h-24 md:h-28 w-auto max-w-full mx-auto" : "h-12 w-auto max-w-full mb-1"}
      />
    );
  }
  return size === "large" ? (
    <ShapeFigure shape={figure} />
  ) : (
    <ShapeFigure shape={figure} className="w-16 h-16 mb-1" />
  );
};

export default QuestionFigure;

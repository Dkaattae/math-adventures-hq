// Static UI configuration shared across screens. Actual questions, users,
// and leaderboard entries come from the backend API (see "@/lib/api") —
// this file only holds display config that has no business being fetched.

export type MathType =
  | "addition"
  | "subtraction"
  | "multiplication"
  | "division"
  | "algebra"
  | "geometry"
  | "fractions"
  | "order_of_operations"
  | "word_problems"
  | "comparison"
  | "money_time"
  | "decimals"
  | "percentages"
  | "measurement"
  | "mixed";
export type Difficulty = "easy" | "medium" | "hard";
export type Grade = "K" | "1" | "2" | "3" | "4" | "5";
export type AnswerMode = "typing" | "multiple_choice";

export const encouragingMessages = [
  "You've got this! Let's have fun with math! 🎉",
  "Math superstar in the making! 🌟",
  "Ready to crush some numbers? Let's go! 💪",
  "Time to show math who's boss! 🚀",
  "Your brain is about to level up! 🧠✨",
];

export const mathTypeLabels: Record<MathType, { label: string; emoji: string }> = {
  addition: { label: "Addition", emoji: "➕" },
  subtraction: { label: "Subtraction", emoji: "➖" },
  multiplication: { label: "Multiplication", emoji: "✖️" },
  division: { label: "Division", emoji: "➗" },
  algebra: { label: "Algebra", emoji: "🔤" },
  geometry: { label: "Geometry", emoji: "📐" },
  fractions: { label: "Fractions", emoji: "🍕" },
  order_of_operations: { label: "Order of Ops", emoji: "🧮" },
  word_problems: { label: "Word Problems", emoji: "📖" },
  comparison: { label: "Comparing", emoji: "⚖️" },
  money_time: { label: "Money & Time", emoji: "💰" },
  decimals: { label: "Decimals", emoji: "🔢" },
  percentages: { label: "Percentages", emoji: "💯" },
  measurement: { label: "Measurement", emoji: "📏" },
  mixed: { label: "Mixed", emoji: "🎲" },
};

export const answerModeConfig: Record<AnswerMode, { label: string; emoji: string }> = {
  typing: { label: "Type it", emoji: "⌨️" },
  multiple_choice: { label: "Multiple choice", emoji: "🔘" },
};

// ---------- grade-appropriate topic gating ----------
// Lowest grade each topic is offered at. Keep in sync with
// _MIN_GRADE_FOR_TYPE in backend/app/questions.py.

const GRADE_RANK: Record<Grade, number> = { K: 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5 };

export const ALL_MATH_TYPES: MathType[] = [
  "addition", "subtraction", "multiplication", "division",
  "algebra", "geometry", "fractions", "order_of_operations",
  "word_problems", "comparison", "money_time", "decimals",
  "percentages", "measurement", "mixed",
];

export const minGradeForType: Record<MathType, Grade> = {
  addition: "K",
  subtraction: "K",
  comparison: "K",
  geometry: "K",
  word_problems: "K",
  mixed: "K",
  money_time: "1",
  fractions: "2",
  multiplication: "2",
  measurement: "2",
  algebra: "2",
  division: "3",
  order_of_operations: "3",
  decimals: "3",
  percentages: "4",
};

export function isTopicAvailable(type: MathType, grade: Grade): boolean {
  return GRADE_RANK[grade] >= GRADE_RANK[minGradeForType[type]];
}

export function topicsForGrade(grade: Grade): MathType[] {
  return ALL_MATH_TYPES.filter((t) => isTopicAvailable(t, grade));
}

// ---------- adaptive level recommendation ----------

const GRADE_ORDER: Grade[] = ["K", "1", "2", "3", "4", "5"];
const DIFFICULTY_ORDER: Difficulty[] = ["easy", "medium", "hard"];

export const gradeLabel = (g: Grade) => (g === "K" ? "Kindergarten" : `Grade ${g}`);

export interface Recommendation {
  kind: "level-up" | "steady" | "ease";
  headline: string;
  detail: string;
  /** Level to start if the player accepts. */
  grade: Grade;
  difficulty: Difficulty;
  /** Button label, or null when there's no different level to move to. */
  cta: string | null;
}

/**
 * Suggest what to do next based on the quiz just finished. A lightweight
 * stand-in for full adaptive difficulty: it reacts to a single score
 * rather than a tracked history, but gives kids the "you're so good,
 * level up!" nudge (or a gentle "let's warm up" when they struggled).
 */
export function recommendNext(
  grade: Grade,
  difficulty: Difficulty,
  score: number,
): Recommendation {
  const gi = GRADE_ORDER.indexOf(grade);
  const di = DIFFICULTY_ORDER.indexOf(difficulty);
  const here = `${gradeLabel(grade)} ${difficulty}`;

  const levelLabel = (g: Grade, d: Difficulty) =>
    g === grade ? `${d} mode` : `${gradeLabel(g)} (${d})`;

  if (score >= 9) {
    let next: { grade: Grade; difficulty: Difficulty } | null = null;
    if (di < DIFFICULTY_ORDER.length - 1) next = { grade, difficulty: DIFFICULTY_ORDER[di + 1] };
    else if (gi < GRADE_ORDER.length - 1) next = { grade: GRADE_ORDER[gi + 1], difficulty: "easy" };

    if (!next) {
      return {
        kind: "level-up",
        headline: "🏆 Legend!",
        detail: `${score}/10 on the very hardest level — ${here}. You've mastered it all!`,
        grade,
        difficulty,
        cta: null,
      };
    }
    const label = levelLabel(next.grade, next.difficulty);
    return {
      kind: "level-up",
      headline: "🌟 Wow, you're on fire!",
      detail: `You aced ${here} with ${score}/10 — you're so good, you're ready for ${label}!`,
      grade: next.grade,
      difficulty: next.difficulty,
      cta: `Try ${label} →`,
    };
  }

  if (score <= 4) {
    let next: { grade: Grade; difficulty: Difficulty } | null = null;
    if (di > 0) next = { grade, difficulty: DIFFICULTY_ORDER[di - 1] };
    else if (gi > 0) next = { grade: GRADE_ORDER[gi - 1], difficulty: "hard" };

    if (!next) {
      return {
        kind: "ease",
        headline: "🌱 Keep going!",
        detail: `Every math star started right here. Want another go at ${here}?`,
        grade,
        difficulty,
        cta: "Try again →",
      };
    }
    const label = levelLabel(next.grade, next.difficulty);
    return {
      kind: "ease",
      headline: "🤗 Good effort!",
      detail: `${here} is tricky — ${score}/10 is a solid start. Want to warm up with ${label} first?`,
      grade: next.grade,
      difficulty: next.difficulty,
      cta: `Try ${label} →`,
    };
  }

  return {
    kind: "steady",
    headline: "💪 Nice work!",
    detail: `You're getting the hang of ${here} with ${score}/10. A little more practice and you'll ace it!`,
    grade,
    difficulty,
    cta: "Practice again →",
  };
}

export const difficultyConfig: Record<Difficulty, { label: string; emoji: string; color: string }> = {
  easy: { label: "Easy", emoji: "😊", color: "fun-green" },
  medium: { label: "Medium", emoji: "🤔", color: "fun-orange" },
  hard: { label: "Hard", emoji: "🔥", color: "fun-pink" },
};

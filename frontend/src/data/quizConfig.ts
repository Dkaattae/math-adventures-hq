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
//
// The ladder logic (which way is "up") lives on the server in one place
// (app/leveling.py). The quiz-submit response carries a ServerRecommendation
// — the direction plus the target level — and this module only turns that
// decision into kid-facing text, so the two can never disagree.

export const gradeLabel = (g: Grade) => (g === "K" ? "Kindergarten" : `Grade ${g}`);

export interface ServerRecommendation {
  direction: "up" | "steady" | "down";
  grade: Grade;
  difficulty: Difficulty;
}

export interface Recommendation {
  headline: string;
  detail: string;
  /** Level to start if the player accepts. */
  grade: Grade;
  difficulty: Difficulty;
  /** Button label, or null when there's no different level to move to. */
  cta: string | null;
}

/**
 * Build the kid-facing recommendation card from the level just played and
 * the server's decision about what to play next.
 */
export function recommendationText(
  current: { grade: Grade; difficulty: Difficulty },
  server: ServerRecommendation,
  score: number,
): Recommendation {
  const here = `${gradeLabel(current.grade)} ${current.difficulty}`;
  const sameLevel = server.grade === current.grade && server.difficulty === current.difficulty;
  const targetLabel =
    server.grade === current.grade
      ? `${server.difficulty} mode`
      : `${gradeLabel(server.grade)} (${server.difficulty})`;

  if (server.direction === "up") {
    if (sameLevel) {
      return {
        headline: "🏆 Legend!",
        detail: `${score}/10 on the very hardest level — ${here}. You've mastered it all!`,
        grade: server.grade,
        difficulty: server.difficulty,
        cta: null,
      };
    }
    return {
      headline: "🌟 Wow, you're on fire!",
      detail: `You aced ${here} with ${score}/10 — you're so good, you're ready for ${targetLabel}!`,
      grade: server.grade,
      difficulty: server.difficulty,
      cta: `Try ${targetLabel} →`,
    };
  }

  if (server.direction === "down") {
    if (sameLevel) {
      return {
        headline: "🌱 Keep going!",
        detail: `Every math star started right here. Want another go at ${here}?`,
        grade: server.grade,
        difficulty: server.difficulty,
        cta: "Try again →",
      };
    }
    return {
      headline: "🤗 Good effort!",
      detail: `${here} is tricky — ${score}/10 is a solid start. Want to warm up with ${targetLabel} first?`,
      grade: server.grade,
      difficulty: server.difficulty,
      cta: `Try ${targetLabel} →`,
    };
  }

  return {
    headline: "💪 Nice work!",
    detail: `You're getting the hang of ${here} with ${score}/10. A little more practice and you'll ace it!`,
    grade: server.grade,
    difficulty: server.difficulty,
    cta: "Practice again →",
  };
}

export const difficultyConfig: Record<Difficulty, { label: string; emoji: string; color: string }> = {
  easy: { label: "Easy", emoji: "😊", color: "fun-green" },
  medium: { label: "Medium", emoji: "🤔", color: "fun-orange" },
  hard: { label: "Hard", emoji: "🔥", color: "fun-pink" },
};

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
  | "order_of_operations";
export type Difficulty = "easy" | "medium" | "hard";
export type Grade = "K" | "1" | "2" | "3" | "4" | "5";

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
};

export const difficultyConfig: Record<Difficulty, { label: string; emoji: string; color: string }> = {
  easy: { label: "Easy", emoji: "😊", color: "fun-green" },
  medium: { label: "Medium", emoji: "🤔", color: "fun-orange" },
  hard: { label: "Hard", emoji: "🔥", color: "fun-pink" },
};

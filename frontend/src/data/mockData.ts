export const existingUsernames = ["Emma", "Liam", "Sophia", "Noah", "Ava", "MathKing", "StarGirl"];

export const leaderboard = [
  { name: "Emma", score: 10, total: 10, time: "1m 20s", badge: "🏆" },
  { name: "Liam", score: 9, total: 10, time: "1m 45s", badge: "🥈" },
  { name: "Sophia", score: 9, total: 10, time: "2m 01s", badge: "🥉" },
  { name: "Noah", score: 8, total: 10, time: "1m 55s", badge: "⭐" },
  { name: "Ava", score: 7, total: 10, time: "2m 10s", badge: "⭐" },
];

export type MathType = "addition" | "subtraction" | "multiplication" | "division" | "algebra" | "geometry";
export type Difficulty = "easy" | "medium" | "hard";
export type Grade = "K" | "1" | "2" | "3" | "4" | "5";

export interface Question {
  id: number;
  question: string;
  correctAnswer: number | string;
  explanation: string;
}

function rand(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getDifficultyRange(difficulty: Difficulty, grade: Grade): [number, number] {
  const g = grade === "K" ? 0 : parseInt(grade);
  const base = g * 3;
  if (difficulty === "easy") return [1, base + 5];
  if (difficulty === "medium") return [2, base + 10];
  return [5, base + 20];
}

export function generateQuestions(mathType: MathType, difficulty: Difficulty, grade: Grade): Question[] {
  const [min, max] = getDifficultyRange(difficulty, grade);
  const questions: Question[] = [];

  for (let i = 0; i < 10; i++) {
    let q: Question;
    const a = rand(min, max);
    const b = rand(min, Math.min(a, max));

    switch (mathType) {
      case "addition":
        q = {
          id: i,
          question: `${a} + ${b} = ?`,
          correctAnswer: a + b,
          explanation: `${a} + ${b} = ${a + b}. Try counting ${b} more after ${a}! 🤓`,
        };
        break;
      case "subtraction":
        q = {
          id: i,
          question: `${a} - ${b} = ?`,
          correctAnswer: a - b,
          explanation: `${a} - ${b} = ${a - b}. Start at ${a} and count back ${b}! 👆`,
        };
        break;
      case "multiplication": {
        const m1 = rand(1, Math.ceil(max / 2));
        const m2 = rand(1, Math.ceil(max / 3));
        q = {
          id: i,
          question: `${m1} × ${m2} = ?`,
          correctAnswer: m1 * m2,
          explanation: `${m1} × ${m2} = ${m1 * m2}. Think of ${m1} groups of ${m2}! 🎯`,
        };
        break;
      }
      case "division": {
        const divisor = rand(1, Math.ceil(max / 3));
        const answer = rand(1, Math.ceil(max / 2));
        const dividend = divisor * answer;
        q = {
          id: i,
          question: `${dividend} ÷ ${divisor} = ?`,
          correctAnswer: answer,
          explanation: `${dividend} ÷ ${divisor} = ${answer}. ${dividend} split into ${divisor} equal groups gives ${answer}! 🍰`,
        };
        break;
      }
      case "algebra": {
        const x = rand(min, max);
        const c = rand(1, max);
        q = {
          id: i,
          question: `x + ${c} = ${x + c}. What is x?`,
          correctAnswer: x,
          explanation: `x = ${x}. Since x + ${c} = ${x + c}, we subtract ${c} from both sides! 🧠`,
        };
        break;
      }
      case "geometry": {
        const shapes = [
          { q: "How many sides does a triangle have?", a: 3, e: "A triangle always has 3 sides! 📐" },
          { q: "How many sides does a square have?", a: 4, e: "A square has 4 equal sides! ⬜" },
          { q: "How many sides does a pentagon have?", a: 5, e: "Penta means 5, so 5 sides! ⭐" },
          { q: "How many sides does a hexagon have?", a: 6, e: "Hexa means 6, so 6 sides! 🔷" },
          { q: "How many degrees in a right angle?", a: 90, e: "A right angle is always 90°! 📏" },
          { q: "How many sides does an octagon have?", a: 8, e: "Octa means 8 — like an octopus! 🐙" },
          { q: "How many corners does a rectangle have?", a: 4, e: "A rectangle has 4 corners (vertices)! 🟩" },
          { q: "How many degrees in a straight line?", a: 180, e: "A straight angle is 180°! 📏" },
          { q: "How many faces does a cube have?", a: 6, e: "A cube has 6 square faces! 🎲" },
          { q: "How many edges does a cube have?", a: 12, e: "A cube has 12 edges! 📦" },
        ];
        const s = shapes[i % shapes.length];
        q = { id: i, question: s.q, correctAnswer: s.a, explanation: s.e };
        break;
      }
      default:
        q = { id: i, question: `${a} + ${b} = ?`, correctAnswer: a + b, explanation: `${a} + ${b} = ${a + b}` };
    }
    questions.push(q);
  }
  return questions;
}

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
};

export const difficultyConfig: Record<Difficulty, { label: string; emoji: string; color: string }> = {
  easy: { label: "Easy", emoji: "😊", color: "fun-green" },
  medium: { label: "Medium", emoji: "🤔", color: "fun-orange" },
  hard: { label: "Hard", emoji: "🔥", color: "fun-pink" },
};

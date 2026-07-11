// Thin fetch wrapper around the FastAPI backend (see /openapi.yaml).
// In dev, Vite proxies /api to http://localhost:8000 (see vite.config.ts).
import type { Difficulty, Grade, MathType } from "@/data/quizConfig";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export interface Question {
  id: number;
  question: string;
}

export interface QuestionResult {
  id: number;
  question: string;
  correctAnswer: number | string;
  explanation: string;
  userAnswer: string | null;
  isCorrect: boolean;
}

export interface Quiz {
  id: string;
  username: string;
  grade: Grade;
  mathType: MathType;
  difficulty: Difficulty;
  questions: Question[];
  createdAt: string;
}

export interface QuizResult {
  quizId: string;
  username: string;
  score: number;
  total: number;
  timeUsedSeconds: number;
  badge: string | null;
  results: QuestionResult[];
  submittedAt: string;
}

export interface LeaderboardEntry {
  name: string;
  score: number;
  total: number;
  timeUsedSeconds: number;
  time: string;
  badge: string | null;
  mathType?: MathType;
  difficulty?: Difficulty;
  grade?: Grade;
  achievedAt: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });

  if (!res.ok) {
    let code = "unknown_error";
    let message = res.statusText;
    try {
      const body = await res.json();
      const detail = body?.detail ?? body;
      code = detail?.code ?? code;
      message = detail?.message ?? message;
    } catch {
      // response had no JSON body — fall back to statusText
    }
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function createUser(username: string) {
  return request<{ username: string; createdAt: string }>("/api/users", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

export function createQuiz(payload: {
  username: string;
  grade: Grade;
  mathType: MathType;
  difficulty: Difficulty;
}) {
  return request<Quiz>("/api/quizzes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitQuiz(
  quizId: string,
  payload: { answers: (string | null)[]; timeUsedSeconds: number },
) {
  return request<QuizResult>(`/api/quizzes/${quizId}/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getLeaderboard(params?: {
  mathType?: MathType;
  difficulty?: Difficulty;
  grade?: Grade;
  limit?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.mathType) qs.set("mathType", params.mathType);
  if (params?.difficulty) qs.set("difficulty", params.difficulty);
  if (params?.grade) qs.set("grade", params.grade);
  if (params?.limit) qs.set("limit", String(params.limit));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<LeaderboardEntry[]>(`/api/leaderboard${suffix}`);
}

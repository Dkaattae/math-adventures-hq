// Thin fetch wrapper around the FastAPI backend (see /openapi.yaml).
// In dev, Vite proxies /api to http://localhost:8000 (see vite.config.ts).
import type { AnswerMode, Difficulty, Grade, MathType } from "@/data/quizConfig";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** What the answer looks like, so we can pick a phone keyboard. */
export type AnswerKind = "integer" | "decimal" | "text";

export interface Question {
  id: number;
  question: string;
  // Present only for multiple-choice quizzes.
  options?: string[] | null;
  // Present for visual geometry: a shape name to draw (e.g. "pentagon").
  figure?: string | null;
  answerKind?: AnswerKind;
  /** Seconds on the clock for this question — long scenes need reading time. */
  timeLimitSeconds?: number;
}

export interface QuestionResult {
  id: number;
  question: string;
  correctAnswer: number | string;
  explanation: string;
  userAnswer: string | null;
  isCorrect: boolean;
  figure?: string | null;
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

export interface Recommendation {
  direction: "up" | "steady" | "down";
  grade: Grade;
  difficulty: Difficulty;
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
  recommendation?: Recommendation | null;
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

// Session token from signup / login / PIN reset. Kept in memory only:
// a reload drops you back at the login screen anyway, so there's nothing
// to gain from persisting it (and one less thing to leak on a shared
// family computer).
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken() {
  return authToken;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(init?.headers ?? {}),
    },
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

interface AuthenticatedUser {
  username: string;
  createdAt: string;
  /** Session token for the player's own endpoints (progress, suggested level). */
  token: string;
}

/** Signup/login/reset all hand back a session; remember it for later calls. */
async function authenticate<T extends AuthenticatedUser>(
  path: string,
  body: Record<string, string>,
): Promise<T> {
  const user = await request<T>(path, { method: "POST", body: JSON.stringify(body) });
  setAuthToken(user.token);
  return user;
}

export function createUser(username: string, pin: string) {
  // recoveryCode is returned exactly once, at signup — show it to the
  // player immediately; it can never be fetched again.
  return authenticate<AuthenticatedUser & { recoveryCode: string }>("/api/users", {
    username,
    pin,
  });
}

export function login(username: string, pin: string) {
  return authenticate<AuthenticatedUser>("/api/users/login", { username, pin });
}

export function resetPin(username: string, recoveryCode: string, newPin: string) {
  return authenticate<AuthenticatedUser>("/api/users/reset-pin", {
    username,
    recoveryCode,
    newPin,
  });
}

export function checkUsername(username: string) {
  const qs = new URLSearchParams({ username });
  return request<{ username: string; available: boolean }>(`/api/users/check?${qs}`);
}

export interface TopicStat {
  mathType: MathType;
  quizzes: number;
  averageScore: number;
  bestScore: number;
}

export interface RecentQuiz {
  mathType: MathType | null;
  grade: Grade | null;
  difficulty: Difficulty | null;
  score: number;
  total: number;
  time: string;
  achievedAt: string;
}

export interface UserStats {
  username: string;
  totalQuizzes: number;
  averageScore: number;
  bestScore: number;
  byTopic: TopicStat[];
  recent: RecentQuiz[];
}

export interface SuggestedLevel {
  grade: Grade;
  difficulty: Difficulty;
  /** Recent quizzes behind the suggestion; 0 = topic never played. */
  basedOn: number;
  mathType?: MathType | null;
}

export function getUserStats(username: string) {
  return request<UserStats>(`/api/users/${encodeURIComponent(username)}/stats`);
}

export function getSuggestedLevel(username: string, mathType?: MathType) {
  const qs = mathType ? `?${new URLSearchParams({ mathType })}` : "";
  return request<SuggestedLevel | null>(
    `/api/users/${encodeURIComponent(username)}/suggested-level${qs}`,
  );
}

export function createQuiz(payload: {
  username: string;
  grade: Grade;
  mathType: MathType;
  difficulty: Difficulty;
  answerMode?: AnswerMode;
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

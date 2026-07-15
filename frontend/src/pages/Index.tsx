import { useState, useCallback } from "react";
import UsernameScreen from "@/components/UsernameScreen";
import SetupScreen from "@/components/SetupScreen";
import QuizScreen from "@/components/QuizScreen";
import ResultsScreen from "@/components/ResultsScreen";
import ProgressScreen from "@/components/ProgressScreen";
import type { MathType, Difficulty, Grade, AnswerMode } from "@/data/quizConfig";
import { createQuiz, submitQuiz, type Question, type QuizResult } from "@/lib/api";

type Screen = "username" | "setup" | "quiz" | "results" | "progress" | "error";

const Index = () => {
  const [screen, setScreen] = useState<Screen>("username");
  const [username, setUsername] = useState("");
  const [quizId, setQuizId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [config, setConfig] = useState<{
    grade: Grade; mathType: MathType; difficulty: Difficulty; answerMode: AnswerMode;
  } | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const handleUsername = (name: string) => {
    setUsername(name);
    setScreen("setup");
  };

  const startQuiz = async (
    grade: Grade, mathType: MathType, difficulty: Difficulty, answerMode: AnswerMode,
  ) => {
    try {
      const quiz = await createQuiz({ username, grade, mathType, difficulty, answerMode });
      setConfig({ grade, mathType, difficulty, answerMode });
      setQuizId(quiz.id);
      setQuestions(quiz.questions);
      setScreen("quiz");
    } catch {
      setErrorMessage("Couldn't start a new quiz. Please check your connection and try again.");
      setScreen("error");
    }
  };

  const handleFinish = useCallback(async (answers: (string | null)[], timeUsed: number) => {
    if (!quizId) return;
    try {
      const result = await submitQuiz(quizId, { answers, timeUsedSeconds: timeUsed });
      setQuizResult(result);
      setScreen("results");
    } catch {
      setErrorMessage("Couldn't submit your answers. Please check your connection and try again.");
      setScreen("error");
    }
  }, [quizId]);

  const handleRedo = () => {
    if (config) startQuiz(config.grade, config.mathType, config.difficulty, config.answerMode);
  };

  const handleTryLevel = (grade: Grade, difficulty: Difficulty) => {
    if (config) startQuiz(grade, config.mathType, difficulty, config.answerMode);
  };

  return (
    <>
      {screen === "username" && <UsernameScreen onSubmit={handleUsername} />}
      {screen === "setup" && (
        <SetupScreen
          username={username}
          onStart={startQuiz}
          onShowProgress={() => setScreen("progress")}
        />
      )}
      {screen === "progress" && (
        <ProgressScreen username={username} onBack={() => setScreen("setup")} />
      )}
      {screen === "quiz" && <QuizScreen questions={questions} onFinish={handleFinish} />}
      {screen === "results" && quizResult && (
        <ResultsScreen
          result={quizResult}
          level={config ? { grade: config.grade, difficulty: config.difficulty } : undefined}
          onTryLevel={handleTryLevel}
          onRedo={handleRedo}
          onHome={() => setScreen("username")}
        />
      )}
      {screen === "error" && (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 text-center">
          <p className="text-4xl">😵</p>
          <p className="font-heading font-semibold text-lg">{errorMessage}</p>
          <button
            onClick={() => setScreen("username")}
            className="px-6 py-3 rounded-2xl bg-primary text-primary-foreground font-heading font-bold"
          >
            🏠 Back Home
          </button>
        </div>
      )}
    </>
  );
};

export default Index;

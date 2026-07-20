import { useState, useCallback } from "react";
import UsernameScreen from "@/components/UsernameScreen";
import SetupScreen from "@/components/SetupScreen";
import QuizScreen from "@/components/QuizScreen";
import ResultsScreen from "@/components/ResultsScreen";
import ProgressScreen from "@/components/ProgressScreen";
import type { MathType, Difficulty, Grade, AnswerMode } from "@/data/quizConfig";
import { ApiError, createQuiz, submitQuiz, type Question, type QuizResult } from "@/lib/api";

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
    // A new quiz invalidates any unsubmitted answers from an old one.
    setPendingSubmission(null);
    setCanRetry(false);
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

  // A finished quiz's answers are kept until they're safely submitted,
  // so a network blip never throws away 10 answers (PROJECT_PLAN §3.2.1).
  const [pendingSubmission, setPendingSubmission] = useState<{
    answers: (string | null)[]; timeUsed: number;
  } | null>(null);
  const [canRetry, setCanRetry] = useState(false);

  const submitAnswers = useCallback(async (answers: (string | null)[], timeUsed: number) => {
    if (!quizId) return;
    try {
      const result = await submitQuiz(quizId, { answers, timeUsedSeconds: timeUsed });
      setQuizResult(result);
      setPendingSubmission(null);
      setScreen("results");
    } catch (err) {
      if (err instanceof ApiError && err.code === "already_submitted") {
        // The first submit actually landed; a retry can't recover the
        // result, so send them home rather than looping.
        setErrorMessage("This quiz was already turned in — start a fresh one!");
        setCanRetry(false);
      } else {
        setErrorMessage("Couldn't submit your answers — but they're safe! Check your connection and try again.");
        setCanRetry(true);
      }
      setScreen("error");
    }
  }, [quizId]);

  const handleFinish = useCallback((answers: (string | null)[], timeUsed: number) => {
    setPendingSubmission({ answers, timeUsed });
    submitAnswers(answers, timeUsed);
  }, [submitAnswers]);

  const handleRetry = () => {
    if (pendingSubmission) submitAnswers(pendingSubmission.answers, pendingSubmission.timeUsed);
  };

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
          <div className="flex flex-wrap gap-3 justify-center">
            {canRetry && pendingSubmission && (
              <button
                onClick={handleRetry}
                className="px-6 py-3 rounded-2xl bg-primary text-primary-foreground font-heading font-bold"
              >
                🔄 Try again
              </button>
            )}
            <button
              onClick={() => setScreen("username")}
              className="px-6 py-3 rounded-2xl bg-card border-2 border-border font-heading font-bold"
            >
              🏠 Back Home
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default Index;

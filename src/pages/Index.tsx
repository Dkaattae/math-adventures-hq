import { useState, useCallback } from "react";
import UsernameScreen from "@/components/UsernameScreen";
import SetupScreen from "@/components/SetupScreen";
import QuizScreen from "@/components/QuizScreen";
import ResultsScreen from "@/components/ResultsScreen";
import {
  type MathType, type Difficulty, type Grade,
  type Question, generateQuestions,
} from "@/data/mockData";

type Screen = "username" | "setup" | "quiz" | "results";

const Index = () => {
  const [screen, setScreen] = useState<Screen>("username");
  const [username, setUsername] = useState("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<(string | null)[]>([]);
  const [timeUsed, setTimeUsed] = useState(0);
  const [config, setConfig] = useState<{ grade: Grade; mathType: MathType; difficulty: Difficulty } | null>(null);

  const handleUsername = (name: string) => {
    setUsername(name);
    setScreen("setup");
  };

  const handleStart = (grade: Grade, mathType: MathType, difficulty: Difficulty) => {
    setConfig({ grade, mathType, difficulty });
    setQuestions(generateQuestions(mathType, difficulty, grade));
    setScreen("quiz");
  };

  const handleFinish = useCallback((ans: (string | null)[], time: number) => {
    setAnswers(ans);
    setTimeUsed(time);
    setScreen("results");
  }, []);

  const handleRedo = () => {
    if (config) {
      setQuestions(generateQuestions(config.mathType, config.difficulty, config.grade));
      setScreen("quiz");
    }
  };

  return (
    <>
      {screen === "username" && <UsernameScreen onSubmit={handleUsername} />}
      {screen === "setup" && <SetupScreen username={username} onStart={handleStart} />}
      {screen === "quiz" && <QuizScreen questions={questions} onFinish={handleFinish} />}
      {screen === "results" && (
        <ResultsScreen
          questions={questions}
          answers={answers}
          timeUsed={timeUsed}
          onRedo={handleRedo}
          onHome={() => setScreen("username")}
        />
      )}
    </>
  );
};

export default Index;

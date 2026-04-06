import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import confetti from "canvas-confetti";
import type { Question } from "@/data/mockData";

interface Props {
  questions: Question[];
  answers: (string | null)[];
  timeUsed: number;
  onRedo: () => void;
  onHome: () => void;
}

const ResultsScreen = ({ questions, answers, timeUsed, onRedo, onHome }: Props) => {
  const [showExplanations, setShowExplanations] = useState(false);

  const results = questions.map((q, i) => ({
    ...q,
    userAnswer: answers[i],
    correct: answers[i] !== null && String(q.correctAnswer) === answers[i],
  }));
  const score = results.filter((r) => r.correct).length;
  const mins = Math.floor(timeUsed / 60);
  const secs = timeUsed % 60;

  useEffect(() => {
    if (score >= 7) {
      confetti({ particleCount: 150, spread: 80, origin: { y: 0.6 } });
    }
  }, [score]);

  const wrongOnes = results.filter((r) => !r.correct);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen flex flex-col items-center p-6 py-10">
      {/* Score */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", bounce: 0.5 }}
        className="text-center mb-8"
      >
        <p className="text-6xl mb-2">{score >= 9 ? "🏆" : score >= 7 ? "🌟" : score >= 5 ? "👍" : "💪"}</p>
        <h1 className="text-4xl font-heading font-bold">
          {score}/10
        </h1>
        <p className="text-muted-foreground font-body mt-1">
          ⏱ {mins}m {secs.toString().padStart(2, "0")}s
        </p>
        <p className="font-heading font-semibold mt-2 text-lg">
          {score === 10 ? "Perfect! You're a math genius! 🎉" :
           score >= 7 ? "Great job! Keep it up! 🌟" :
           score >= 5 ? "Nice try! Practice makes perfect! 💪" :
           "Don't give up! You'll get better! 🤗"}
        </p>
      </motion.div>

      {/* Question Review */}
      <div className="w-full max-w-lg space-y-3 mb-8">
        {results.map((r, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className={`p-4 rounded-xl border-2 ${r.correct ? "border-success/40 bg-success/5" : "border-destructive/40 bg-destructive/5"}`}
          >
            <div className="flex items-start gap-3">
              <span className="text-xl">{r.correct ? "✅" : "❌"}</span>
              <div className="flex-1">
                <p className="font-heading font-semibold">{r.question}</p>
                <p className="text-sm text-muted-foreground">
                  Your answer: <span className="font-bold">{r.userAnswer ?? "—"}</span>
                  {!r.correct && (
                    <> · Correct: <span className="font-bold text-success">{String(r.correctAnswer)}</span></>
                  )}
                </p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Buttons */}
      <div className="flex flex-wrap gap-3 justify-center mb-8">
        <ActionBtn onClick={onRedo} primary>🔄 Redo Practice</ActionBtn>
        {wrongOnes.length > 0 && (
          <ActionBtn onClick={() => setShowExplanations(!showExplanations)}>
            {showExplanations ? "Hide Explanations" : "💡 Explain My Errors"}
          </ActionBtn>
        )}
        <ActionBtn onClick={onHome}>🏠 Home</ActionBtn>
      </div>

      {/* Explanations */}
      <AnimatePresence>
        {showExplanations && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="w-full max-w-lg space-y-3 overflow-hidden"
          >
            <h2 className="text-xl font-heading font-bold text-center mb-4">📚 Let's Learn!</h2>
            {wrongOnes.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="p-4 rounded-xl bg-card border-2 border-secondary/40"
              >
                <p className="font-heading font-semibold mb-1">{r.question}</p>
                <p className="text-sm font-body text-muted-foreground">{r.explanation}</p>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const ActionBtn = ({ children, onClick, primary }: {
  children: React.ReactNode; onClick: () => void; primary?: boolean;
}) => (
  <motion.button
    whileHover={{ scale: 1.05 }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    className={`px-6 py-3 rounded-2xl font-heading font-bold text-base transition-all ${
      primary
        ? "bg-primary text-primary-foreground shadow-lg"
        : "bg-card border-2 border-border hover:border-primary/40"
    }`}
  >
    {children}
  </motion.button>
);

export default ResultsScreen;

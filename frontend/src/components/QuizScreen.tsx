import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Question } from "@/lib/api";
import ShapeFigure from "./ShapeFigure";

interface Props {
  questions: Question[];
  onFinish: (answers: (string | null)[], timeUsed: number) => void;
}

const QUESTION_TIME = 15;
const TOTAL_TIME = 180;

const QuizScreen = ({ questions, onFinish }: Props) => {
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<(string | null)[]>(Array(10).fill(null));
  const [inputVal, setInputVal] = useState("");
  const [questionTimer, setQuestionTimer] = useState(QUESTION_TIME);
  const [totalTimer, setTotalTimer] = useState(TOTAL_TIME);
  const [flagged, setFlagged] = useState<Set<number>>(new Set());
  const [reviewing, setReviewing] = useState(false);
  // The backend never sends the correct answer before the quiz is
  // submitted (anti-cheat), so this is just a "your answer was saved"
  // pulse rather than a correct/wrong indicator.
  const [feedback, setFeedback] = useState<"saved" | null>(null);

  // Countdowns are computed from fixed deadline timestamps, not by
  // decrementing state on each tick. A decrementing interval gets torn
  // down and recreated whenever its deps change, which paused the clock
  // while the player was typing.
  const totalDeadline = useRef(Date.now() + TOTAL_TIME * 1000);
  const questionDeadline = useRef(Date.now() + QUESTION_TIME * 1000);
  const finished = useRef(false);

  // Latest state, readable from inside the single long-lived interval.
  const latest = useRef({ answers, inputVal, current });
  useEffect(() => {
    latest.current = { answers, inputVal, current };
  });

  const finish = useCallback(() => {
    if (finished.current) return;
    finished.current = true;
    const { answers, inputVal, current } = latest.current;
    const finalAnswers = [...answers];
    if (inputVal.trim() && finalAnswers[current] === null) {
      finalAnswers[current] = inputVal.trim();
    }
    const secondsLeft = Math.max(0, Math.ceil((totalDeadline.current - Date.now()) / 1000));
    onFinish(finalAnswers, TOTAL_TIME - secondsLeft);
  }, [onFinish]);

  // Single interval drives both countdowns for the quiz's whole lifetime.
  useEffect(() => {
    const tick = () => {
      const now = Date.now();
      const totalLeft = Math.max(0, Math.ceil((totalDeadline.current - now) / 1000));
      setTotalTimer(totalLeft);
      if (totalLeft <= 0) {
        finish();
        return;
      }

      const questionLeft = Math.max(0, Math.ceil((questionDeadline.current - now) / 1000));
      setQuestionTimer(questionLeft);
      if (questionLeft <= 0) {
        const { answers, inputVal, current } = latest.current;
        // Time's up on this question — keep whatever was typed.
        if (inputVal.trim() && answers[current] === null) {
          const salvaged = inputVal.trim();
          setAnswers((prev) => {
            const next = [...prev];
            next[current] = salvaged;
            return next;
          });
        }
        if (current >= 9) {
          finish();
          return;
        }
        setCurrent(current + 1);
        questionDeadline.current = now + QUESTION_TIME * 1000;
      }
    };
    const t = setInterval(tick, 250);
    return () => clearInterval(t);
  }, [finish]);

  // Fresh 15 seconds whenever the player lands on a question, including
  // manual Next/Review navigation.
  useEffect(() => {
    questionDeadline.current = Date.now() + QUESTION_TIME * 1000;
    setQuestionTimer(QUESTION_TIME);
  }, [current]);

  useEffect(() => {
    setInputVal(answers[current] ?? "");
  }, [current, answers]);

  const recordAndAdvance = (value: string) => {
    const newAnswers = [...answers];
    newAnswers[current] = value;
    setAnswers(newAnswers);

    setFeedback("saved");
    setTimeout(() => {
      setFeedback(null);
      if (current < 9) setCurrent(current + 1);
    }, 400);
  };

  const submitAnswer = () => {
    if (!inputVal.trim()) return;
    recordAndAdvance(inputVal.trim());
  };

  const chooseOption = (option: string) => recordAndAdvance(option);

  const goNext = () => {
    if (current < 9) setCurrent(current + 1);
  };

  const toggleFlag = () => {
    const f = new Set(flagged);
    if (f.has(current)) f.delete(current); else f.add(current);
    setFlagged(f);
  };

  const totalMins = Math.floor(totalTimer / 60);
  const totalSecs = totalTimer % 60;
  const progress = ((current + 1) / 10) * 100;
  const qTimerUrgent = questionTimer <= 5;
  const options = questions[current].options;
  const isMultipleChoice = Array.isArray(options) && options.length > 0;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen flex flex-col p-4 md:p-6">
      {/* Timers */}
      <div className="flex justify-between items-center mb-4">
        <div className={`font-heading font-bold text-lg px-4 py-2 rounded-xl ${qTimerUrgent ? "bg-destructive text-destructive-foreground animate-pulse" : "bg-card border border-border"}`}>
          ⏱ {questionTimer}s
        </div>
        <div className="font-heading font-semibold text-muted-foreground">
          {totalMins}:{totalSecs.toString().padStart(2, "0")} left
        </div>
      </div>

      {/* Progress */}
      <div className="w-full h-3 bg-muted rounded-full mb-6 overflow-hidden">
        <motion.div
          className="h-full bg-primary rounded-full"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Question */}
      <div className="flex-1 flex flex-col items-center justify-center max-w-lg mx-auto w-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={current}
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            className="w-full space-y-6"
          >
            <p className="text-center text-muted-foreground font-heading font-semibold">
              Question {current + 1} of 10
            </p>
            <div className={`p-8 rounded-3xl border-2 text-center transition-colors ${
              feedback === "saved" ? "bg-success/10 border-success" : "bg-card border-border"
            }`}>
              {questions[current].figure && (
                <div className="mb-4">
                  <ShapeFigure shape={questions[current].figure!} />
                </div>
              )}
              <p className="text-2xl md:text-3xl font-heading font-bold">
                {questions[current].question}
              </p>
            </div>
            {isMultipleChoice ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {options!.map((opt) => {
                  const chosen = answers[current] === opt;
                  return (
                    <motion.button
                      key={opt}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => chooseOption(opt)}
                      className={`px-5 py-4 text-xl rounded-2xl border-2 font-heading transition-all ${
                        chosen
                          ? "bg-primary text-primary-foreground border-primary shadow-md"
                          : "bg-card border-border hover:border-primary/40"
                      }`}
                    >
                      {opt}
                    </motion.button>
                  );
                })}
              </div>
            ) : (
              <input
                type="text"
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitAnswer()}
                placeholder="Your answer..."
                className="w-full px-5 py-4 text-xl text-center rounded-2xl border-2 border-border bg-card font-heading focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/30 transition-all"
                autoFocus
              />
            )}
          </motion.div>
        </AnimatePresence>

        {feedback && (
          <motion.p
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="text-4xl mt-4"
          >
            📝
          </motion.p>
        )}
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 justify-center mt-6">
        {!isMultipleChoice && (
          <QuizButton onClick={submitAnswer} primary>Submit Answer</QuizButton>
        )}
        <QuizButton onClick={goNext}>Next ➡️</QuizButton>
        <QuizButton onClick={toggleFlag}>
          {flagged.has(current) ? "🚩 Unflag" : "🏳️ Flag"}
        </QuizButton>
        <QuizButton onClick={() => setReviewing(!reviewing)}>
          📋 Review
        </QuizButton>
        <QuizButton onClick={finish} danger>Finish ✅</QuizButton>
      </div>

      {/* Review panel */}
      <AnimatePresence>
        {reviewing && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mt-4"
          >
            <div className="grid grid-cols-5 gap-2 max-w-xs mx-auto">
              {questions.map((_, i) => (
                <button
                  key={i}
                  onClick={() => { setCurrent(i); setReviewing(false); }}
                  className={`p-2 rounded-xl font-heading font-bold text-sm transition-all border-2 ${
                    i === current ? "border-primary bg-primary text-primary-foreground" :
                    answers[i] ? "border-success bg-success/10" :
                    flagged.has(i) ? "border-secondary bg-secondary/20" :
                    "border-border bg-card"
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const QuizButton = ({ children, onClick, primary, danger }: {
  children: React.ReactNode; onClick: () => void; primary?: boolean; danger?: boolean;
}) => (
  <motion.button
    whileHover={{ scale: 1.05 }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    className={`px-5 py-3 rounded-xl font-heading font-semibold text-sm transition-all ${
      primary ? "bg-primary text-primary-foreground shadow-md" :
      danger ? "bg-destructive text-destructive-foreground" :
      "bg-card border-2 border-border hover:border-primary/40"
    }`}
  >
    {children}
  </motion.button>
);

export default QuizScreen;

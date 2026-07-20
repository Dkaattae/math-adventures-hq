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

// Interaction model (PROJECT_PLAN §3.1): review-before-submit. Answers
// only save locally until Finish; Back/Next both keep the typed draft;
// the always-visible dot strip shows blanks and jumps anywhere; Finish
// appears on the last question (or once everything's answered) and warns
// when blanks remain.
const QuizScreen = ({ questions, onFinish }: Props) => {
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<(string | null)[]>(Array(10).fill(null));
  const [inputVal, setInputVal] = useState("");
  const [questionTimer, setQuestionTimer] = useState(QUESTION_TIME);
  const [totalTimer, setTotalTimer] = useState(TOTAL_TIME);
  const [confirmingFinish, setConfirmingFinish] = useState(false);
  // The backend never sends the correct answer before the quiz is
  // submitted (anti-cheat), so this is just a "your answer was saved"
  // pulse (multiple-choice taps), not a correct/wrong indicator.
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
    if (inputVal.trim()) {
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
  // Back/Next and dot-strip navigation; also drop any pending confirm.
  useEffect(() => {
    questionDeadline.current = Date.now() + QUESTION_TIME * 1000;
    setQuestionTimer(QUESTION_TIME);
    setConfirmingFinish(false);
  }, [current]);

  useEffect(() => {
    setInputVal(answers[current] ?? "");
  }, [current, answers]);

  /** Keep the typed draft (non-empty) when leaving a question. */
  const saveDraft = () => {
    const value = inputVal.trim();
    if (!value || answers[current] === value) return;
    setAnswers((prev) => {
      const next = [...prev];
      next[current] = value;
      return next;
    });
  };

  const goTo = (index: number) => {
    if (index === current || index < 0 || index > 9) return;
    saveDraft();
    setCurrent(index);
  };

  const goBack = () => goTo(current - 1);
  const goNext = () => goTo(current + 1);

  // Multiple choice: tapping an option saves it and moves on.
  const chooseOption = (option: string) => {
    const newAnswers = [...answers];
    newAnswers[current] = option;
    setAnswers(newAnswers);

    setFeedback("saved");
    setTimeout(() => {
      setFeedback(null);
      if (current < 9) setCurrent(current + 1);
    }, 400);
  };

  // Blank count as it would stand if we finished right now (the current
  // draft counts as answered).
  const draft = inputVal.trim();
  const effectiveAnswers = answers.map((a, i) => (i === current && draft ? draft : a));
  const blanks = effectiveAnswers.filter((a) => !a).length;
  const allAnswered = blanks === 0;
  const showFinish = current === 9 || allAnswered;

  const requestFinish = () => {
    if (allAnswered) {
      finish();
      return;
    }
    saveDraft();
    setConfirmingFinish(true);
  };

  const goToFirstBlank = () => {
    setConfirmingFinish(false);
    const firstBlank = effectiveAnswers.findIndex((a) => !a);
    if (firstBlank !== -1) goTo(firstBlank);
  };

  const totalMins = Math.floor(totalTimer / 60);
  const totalSecs = totalTimer % 60;
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

      {/* Question dots: progress, review, and navigation in one strip */}
      <div className="flex justify-center gap-1.5 flex-wrap mb-6" role="group" aria-label="Quiz questions">
        {questions.map((_, i) => {
          const answered = Boolean(effectiveAnswers[i]);
          const isCurrent = i === current;
          return (
            <button
              key={i}
              onClick={() => goTo(i)}
              aria-label={`Question ${i + 1}, ${answered ? "answered" : "blank"}${isCurrent ? ", current" : ""}`}
              aria-current={isCurrent ? "step" : undefined}
              className={`w-8 h-8 rounded-full text-xs font-heading font-bold border-2 transition-all ${
                answered
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card border-border text-muted-foreground"
              } ${isCurrent ? "ring-2 ring-primary/50 scale-110" : "hover:border-primary/40"}`}
            >
              {i + 1}
            </button>
          );
        })}
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
                onKeyDown={(e) => e.key === "Enter" && (current < 9 ? goNext() : requestFinish())}
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

      {/* Controls: Back / Next, plus Finish when it makes sense */}
      <div className="flex flex-wrap gap-3 justify-center mt-6">
        {current > 0 && <QuizButton onClick={goBack}>← Back</QuizButton>}
        {current < 9 && (
          <QuizButton onClick={goNext} primary={!isMultipleChoice && !showFinish}>
            Next →
          </QuizButton>
        )}
        {showFinish && (
          <QuizButton onClick={requestFinish} primary>
            Finish ✅
          </QuizButton>
        )}
      </div>

      {/* Blank-question check before finishing early */}
      <AnimatePresence>
        {confirmingFinish && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="mt-4 mx-auto max-w-md p-4 rounded-2xl border-2 border-secondary/60 bg-secondary/10 text-center space-y-3"
          >
            <p className="font-heading font-semibold">
              🤔 You still have {blanks} blank question{blanks === 1 ? "" : "s"}!
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <QuizButton onClick={goToFirstBlank} primary>Keep going 💪</QuizButton>
              <QuizButton onClick={finish}>Finish anyway ✅</QuizButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const QuizButton = ({ children, onClick, primary }: {
  children: React.ReactNode; onClick: () => void; primary?: boolean;
}) => (
  <motion.button
    whileHover={{ scale: 1.05 }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    className={`px-5 py-3 rounded-xl font-heading font-semibold text-sm transition-all ${
      primary ? "bg-primary text-primary-foreground shadow-md" :
      "bg-card border-2 border-border hover:border-primary/40"
    }`}
  >
    {children}
  </motion.button>
);

export default QuizScreen;

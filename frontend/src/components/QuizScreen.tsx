import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Question } from "@/lib/api";
import ShapeFigure from "./ShapeFigure";

interface Props {
  questions: Question[];
  onFinish: (answers: (string | null)[], timeUsed: number) => void;
  /** Abandon the quiz without submitting (PROJECT_PLAN §3.4). */
  onQuit: () => void;
}

const DEFAULT_QUESTION_TIME = 15;
// Slack on top of the per-question budget, so a kid who thinks a little
// longer on one question doesn't lose the quiz. (10 × 15 + 30 = the 180
// seconds every quiz had before questions carried their own clocks.)
const TOTAL_SLACK = 30;
// The whole quiz auto-submits at 0:00, so warn before it happens
// (PROJECT_PLAN §3.1) rather than yanking the page away silently.
const TOTAL_WARNING_TIME = 30;

// Phone keyboards: only promise a numeric keypad when the answer really
// is a non-negative number — keypads have no minus, "/" or letters
// (PROJECT_PLAN §3.2).
const INPUT_MODES = {
  integer: "numeric",
  decimal: "decimal",
  text: "text",
} as const;

// Interaction model (PROJECT_PLAN §3.1): review-before-submit. Answers
// only save locally until Finish; Back/Next both keep the typed draft;
// the always-visible dot strip shows blanks and jumps anywhere; Finish
// appears on the last question (or once everything's answered) and warns
// when blanks remain. There's also a way out that isn't Finish (§3.4).
const QuizScreen = ({ questions, onFinish, onQuit }: Props) => {
  // Each question carries its own budget: a five-line shopping list
  // can't be read in the 15 seconds a "7 + 5" needs. Fixed for the
  // quiz's lifetime, so the deadlines below can lean on it.
  const limits = useRef(
    questions.map((q) => q.timeLimitSeconds ?? DEFAULT_QUESTION_TIME),
  ).current;
  const totalTime = useRef(
    limits.reduce((sum, s) => sum + s, 0) + TOTAL_SLACK,
  ).current;

  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<(string | null)[]>(Array(10).fill(null));
  const [inputVal, setInputVal] = useState("");
  const [questionTimer, setQuestionTimer] = useState(limits[0]);
  const [totalTimer, setTotalTimer] = useState(totalTime);
  const [confirmingFinish, setConfirmingFinish] = useState(false);
  const [confirmingQuit, setConfirmingQuit] = useState(false);
  // The backend never sends the correct answer before the quiz is
  // submitted (anti-cheat), so this is just a "your answer was saved"
  // pulse (multiple-choice taps), not a correct/wrong indicator.
  const [feedback, setFeedback] = useState<"saved" | null>(null);

  // Countdowns are computed from fixed deadline timestamps, not by
  // decrementing state on each tick. A decrementing interval gets torn
  // down and recreated whenever its deps change, which paused the clock
  // while the player was typing.
  const totalDeadline = useRef(Date.now() + totalTime * 1000);
  const questionDeadline = useRef(Date.now() + limits[0] * 1000);
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
    onFinish(finalAnswers, totalTime - secondsLeft);
  }, [onFinish, totalTime]);

  // Walking away without submitting. Flipping the same latch `finish`
  // uses stops the countdown from turning the abandoned answers into a
  // submission on its next tick.
  const quit = useCallback(() => {
    if (finished.current) return;
    finished.current = true;
    onQuit();
  }, [onQuit]);

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
        questionDeadline.current = now + limits[current + 1] * 1000;
      }
    };
    const t = setInterval(tick, 250);
    return () => clearInterval(t);
  }, [finish, limits]);

  // A fresh budget whenever the player lands on a question, including
  // Back/Next and dot-strip navigation; also drop any pending confirm.
  useEffect(() => {
    questionDeadline.current = Date.now() + limits[current] * 1000;
    setQuestionTimer(limits[current]);
    setConfirmingFinish(false);
  }, [current, limits]);

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
  const totalUrgent = totalTimer <= TOTAL_WARNING_TIME;
  const options = questions[current].options;
  const isMultipleChoice = Array.isArray(options) && options.length > 0;
  const inputMode = INPUT_MODES[questions[current].answerKind ?? "text"];
  // A multi-line question is a scene (a list with a question under it),
  // not a one-line sum, and needs to be laid out like one.
  const isScene = questions[current].question.includes("\n");

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen flex flex-col p-4 md:p-6">
      {/* Timers, with the way out parked beside them */}
      <div className="flex justify-between items-center gap-2 mb-4">
        <div className="flex items-center gap-2">
          {/* §3.4: Finish submits and the clock is the only other exit,
              which strands a kid who picked the wrong grade. Small and
              quiet so it isn't mistaken for Next. */}
          <button
            onClick={() => setConfirmingQuit(true)}
            aria-label="Quit this quiz"
            className="w-10 h-10 shrink-0 rounded-xl border border-border bg-card text-muted-foreground text-lg font-heading hover:border-destructive/50 hover:text-destructive transition-colors"
          >
            ✕
          </button>
          <div className={`font-heading font-bold text-lg px-4 py-2 rounded-xl ${qTimerUrgent ? "bg-destructive text-destructive-foreground animate-pulse" : "bg-card border border-border"}`}>
            ⏱ {questionTimer}s
          </div>
        </div>
        <div
          className={`font-heading font-semibold px-3 py-1 rounded-xl ${
            totalUrgent
              ? "bg-destructive text-destructive-foreground animate-pulse"
              : "text-muted-foreground"
          }`}
        >
          {totalUrgent && "⏰ "}
          {totalMins}:{totalSecs.toString().padStart(2, "0")} left
        </div>
      </div>

      {/* The colour change alone wouldn't reach a screen reader (or a
          kid who can't tell red from grey), so say it in words too. */}
      {totalUrgent && (
        <p role="status" className="text-center font-heading font-semibold text-destructive mb-3">
          ⏰ Less than {TOTAL_WARNING_TIME} seconds left — finish up!
        </p>
      )}

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
            <div className={`rounded-3xl border-2 transition-colors ${
              isScene ? "p-5 text-left" : "p-8 text-center"
            } ${
              feedback === "saved" ? "bg-success/10 border-success" : "bg-card border-border"
            }`}>
              {questions[current].figure && (
                <div className="mb-4">
                  <ShapeFigure shape={questions[current].figure!} />
                </div>
              )}
              {/* Word problems arrive as a titled list over several
                  lines, so keep the line breaks and step the type down —
                  a shopping list at 3xl is a wall. */}
              <p
                className={`font-heading font-bold whitespace-pre-line ${
                  isScene ? "text-base md:text-lg leading-relaxed" : "text-2xl md:text-3xl"
                }`}
              >
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
                inputMode={inputMode}
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

      {/* Quitting throws the attempt away, so it asks first — over the
          question rather than under it, where a tap can't land on the
          quiz by accident. The clock keeps running behind it: pausing
          would hand out free thinking time. */}
      <AnimatePresence>
        {confirmingQuit && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-foreground/40"
            onClick={() => setConfirmingQuit(false)}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-labelledby="quit-title"
              initial={{ scale: 0.9, y: 10 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 10 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm p-6 rounded-3xl border-2 border-border bg-card text-center space-y-4 shadow-xl"
            >
              <p id="quit-title" className="font-heading font-bold text-lg">
                🚪 Leave this quiz?
              </p>
              <p className="text-sm text-muted-foreground">
                Your answers won't be saved and this quiz won't count.
              </p>
              <div className="flex flex-wrap gap-3 justify-center">
                <QuizButton onClick={() => setConfirmingQuit(false)} primary>
                  Keep playing 💪
                </QuizButton>
                <QuizButton onClick={quit}>Leave 🚪</QuizButton>
              </div>
            </motion.div>
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

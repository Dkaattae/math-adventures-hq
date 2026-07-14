import { useState } from "react";
import { motion } from "framer-motion";
import {
  type MathType, type Difficulty, type Grade, type AnswerMode,
  mathTypeLabels, difficultyConfig, answerModeConfig, encouragingMessages,
} from "@/data/quizConfig";

interface Props {
  username: string;
  onStart: (grade: Grade, mathType: MathType, difficulty: Difficulty, answerMode: AnswerMode) => void;
}

const grades: Grade[] = ["K", "1", "2", "3", "4", "5"];
const mathTypes: MathType[] = [
  "addition", "subtraction", "multiplication", "division",
  "algebra", "geometry", "fractions", "order_of_operations",
  "word_problems", "comparison", "money_time", "decimals",
  "percentages", "measurement", "mixed",
];
const difficulties: Difficulty[] = ["easy", "medium", "hard"];
const answerModes: AnswerMode[] = ["typing", "multiple_choice"];

const SetupScreen = ({ username, onStart }: Props) => {
  const [grade, setGrade] = useState<Grade | null>(null);
  const [mathType, setMathType] = useState<MathType | null>(null);
  const [difficulty, setDifficulty] = useState<Difficulty | null>(null);
  const [answerMode, setAnswerMode] = useState<AnswerMode>("typing");

  const allSelected = grade && mathType && difficulty;
  const message = encouragingMessages[Math.floor(Math.random() * encouragingMessages.length)];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen flex flex-col items-center p-6 py-10"
    >
      <motion.h1
        initial={{ y: -20 }}
        animate={{ y: 0 }}
        className="text-3xl md:text-4xl font-heading font-bold mb-8"
      >
        Hey {username}! 👋
      </motion.h1>

      <div className="w-full max-w-lg space-y-8">
        {/* Grade */}
        <Section title="Pick your grade 🎒">
          <div className="grid grid-cols-6 gap-2">
            {grades.map((g) => (
              <OptionButton key={g} selected={grade === g} onClick={() => setGrade(g)}>
                {g === "K" ? "K" : g}
              </OptionButton>
            ))}
          </div>
        </Section>

        {/* Math Type */}
        <Section title="What do you want to practice? 🧮">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {mathTypes.map((mt) => (
              <OptionButton key={mt} selected={mathType === mt} onClick={() => setMathType(mt)} wide>
                {mathTypeLabels[mt].emoji} {mathTypeLabels[mt].label}
              </OptionButton>
            ))}
          </div>
        </Section>

        {/* Difficulty */}
        <Section title="How tough? 💪">
          <div className="grid grid-cols-3 gap-2">
            {difficulties.map((d) => (
              <OptionButton key={d} selected={difficulty === d} onClick={() => setDifficulty(d)}>
                {difficultyConfig[d].emoji} {difficultyConfig[d].label}
              </OptionButton>
            ))}
          </div>
        </Section>

        {/* Answer mode */}
        <Section title="How do you want to answer? ✍️">
          <div className="grid grid-cols-2 gap-2">
            {answerModes.map((m) => (
              <OptionButton key={m} selected={answerMode === m} onClick={() => setAnswerMode(m)} wide>
                {answerModeConfig[m].emoji} {answerModeConfig[m].label}
              </OptionButton>
            ))}
          </div>
        </Section>

        {allSelected && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center space-y-4"
          >
            <p className="text-lg font-body text-muted-foreground">
              {message.replace("[Name]", username)}
            </p>
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => onStart(grade!, mathType!, difficulty!, answerMode)}
              className="w-full py-4 rounded-2xl bg-primary text-primary-foreground font-heading font-bold text-xl shadow-lg hover:shadow-xl transition-all"
            >
              Start Practice 🎉
            </motion.button>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}>
    <h2 className="font-heading font-semibold text-lg mb-3">{title}</h2>
    {children}
  </motion.div>
);

const OptionButton = ({
  children, selected, onClick, wide,
}: {
  children: React.ReactNode; selected: boolean; onClick: () => void; wide?: boolean;
}) => (
  <motion.button
    whileHover={{ scale: 1.05 }}
    whileTap={{ scale: 0.95 }}
    onClick={onClick}
    className={`py-3 ${wide ? "px-4" : "px-2"} rounded-xl font-heading font-semibold text-sm transition-all border-2 ${
      selected
        ? "bg-primary text-primary-foreground border-primary shadow-md"
        : "bg-card border-border hover:border-primary/40"
    }`}
  >
    {children}
  </motion.button>
);

export default SetupScreen;

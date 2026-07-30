import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { getLeaderboard } from "@/lib/api";
import {
  type MathType, type Difficulty, type Grade,
  mathTypeLabels, difficultyConfig, ALL_MATH_TYPES,
} from "@/data/quizConfig";

const ALL = "all" as const;
type Filter<T> = T | typeof ALL;

const grades: Grade[] = ["K", "1", "2", "3", "4", "5"];
const difficulties: Difficulty[] = ["easy", "medium", "hard"];

const Leaderboard = () => {
  const [grade, setGrade] = useState<Filter<Grade>>(ALL);
  const [mathType, setMathType] = useState<Filter<MathType>>(ALL);
  const [difficulty, setDifficulty] = useState<Filter<Difficulty>>(ALL);

  const { data: leaderboard = [], isLoading, isError } = useQuery({
    queryKey: ["leaderboard", grade, mathType, difficulty],
    queryFn: () => getLeaderboard({
      limit: 5,
      grade: grade === ALL ? undefined : grade,
      mathType: mathType === ALL ? undefined : mathType,
      difficulty: difficulty === ALL ? undefined : difficulty,
    }),
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-md mx-auto"
    >
      <h2 className="text-2xl font-heading font-bold text-center mb-4 flex items-center justify-center gap-2">
        🏆 Leaderboard
      </h2>

      {/* Filters */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <FilterSelect
          label="Grade"
          value={grade}
          onChange={(v) => setGrade(v as Filter<Grade>)}
          options={grades.map((g) => ({ value: g, label: g === "K" ? "K" : `Grade ${g}` }))}
        />
        <FilterSelect
          label="Topic"
          value={mathType}
          onChange={(v) => setMathType(v as Filter<MathType>)}
          options={ALL_MATH_TYPES.map((t) => ({ value: t, label: mathTypeLabels[t].label }))}
        />
        <FilterSelect
          label="Level"
          value={difficulty}
          onChange={(v) => setDifficulty(v as Filter<Difficulty>)}
          options={difficulties.map((d) => ({ value: d, label: difficultyConfig[d].label }))}
        />
      </div>

      {isLoading ? (
        <p className="text-center text-muted-foreground font-body">Loading leaderboard...</p>
      ) : isError ? (
        <p className="text-center text-muted-foreground font-body">Couldn't load the leaderboard.</p>
      ) : leaderboard.length === 0 ? (
        <p className="text-center text-muted-foreground font-body py-4">
          No scores here yet — be the first! 🚀
        </p>
      ) : (
        <ul className="space-y-2">
          {leaderboard.map((entry, i) => (
            <motion.li
              key={`${entry.name}-${entry.achievedAt}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`flex items-center gap-3 p-3 rounded-xl ${
                i === 0
                  ? "bg-secondary/40 border-2 border-secondary"
                  : "bg-card border border-border"
              }`}
            >
              <span className="text-2xl w-10 text-center">{entry.badge}</span>
              <div className="flex-1 min-w-0">
                <p className="font-heading font-semibold">{entry.name}</p>
                <p className="text-sm text-muted-foreground">⏱ {entry.time}</p>
                {/* Unfiltered, "10/10 — 1m 20s" says nothing about
                    whether it was K-easy or G5-hard, so each row carries
                    its own level. Only chips the row actually has: old
                    rows predate these columns. */}
                <div className="flex flex-wrap gap-1 mt-1">
                  {entry.grade && (
                    <Chip>{entry.grade === "K" ? "K" : `G${entry.grade}`}</Chip>
                  )}
                  {entry.mathType && (
                    <Chip>
                      {mathTypeLabels[entry.mathType].emoji}{" "}
                      {mathTypeLabels[entry.mathType].label}
                    </Chip>
                  )}
                  {entry.difficulty && (
                    <Chip>{difficultyConfig[entry.difficulty].label}</Chip>
                  )}
                </div>
              </div>
              <div className="text-right">
                <p className="font-heading font-bold text-primary">
                  {entry.score}/{entry.total}
                </p>
              </div>
            </motion.li>
          ))}
        </ul>
      )}
    </motion.div>
  );
};

const Chip = ({ children }: { children: React.ReactNode }) => (
  <span className="px-2 py-0.5 rounded-full bg-muted text-muted-foreground text-[11px] font-heading font-semibold whitespace-nowrap">
    {children}
  </span>
);

const FilterSelect = ({
  label, value, onChange, options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) => (
  <label className="flex flex-col gap-1">
    <span className="text-xs font-heading font-semibold text-muted-foreground">{label}</span>
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="px-2 py-2 rounded-xl border-2 border-border bg-card font-body text-sm focus:outline-none focus:border-primary transition-colors"
    >
      <option value="all">All</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  </label>
);

export default Leaderboard;

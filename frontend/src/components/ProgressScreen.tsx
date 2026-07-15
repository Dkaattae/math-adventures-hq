import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { getUserStats } from "@/lib/api";
import { mathTypeLabels, difficultyConfig, type MathType, type Difficulty } from "@/data/quizConfig";

interface Props {
  username: string;
  onBack: () => void;
}

const ProgressScreen = ({ username, onBack }: Props) => {
  const { data: stats, isLoading, isError } = useQuery({
    queryKey: ["stats", username],
    queryFn: () => getUserStats(username),
  });

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen flex flex-col items-center p-6 py-10"
    >
      <h1 className="text-3xl md:text-4xl font-heading font-bold mb-6">
        📊 {username}'s Progress
      </h1>

      {isLoading ? (
        <p className="text-muted-foreground font-body">Loading your stats...</p>
      ) : isError ? (
        <p className="text-muted-foreground font-body">Couldn't load your progress.</p>
      ) : !stats || stats.totalQuizzes === 0 ? (
        <div className="text-center space-y-4">
          <p className="text-5xl">🌱</p>
          <p className="font-heading font-semibold text-lg">No quizzes yet!</p>
          <p className="text-muted-foreground font-body">Play your first quiz and your stats show up here.</p>
        </div>
      ) : (
        <div className="w-full max-w-lg space-y-8">
          {/* Headline numbers */}
          <div className="grid grid-cols-3 gap-3">
            <StatTile label="Quizzes" value={String(stats.totalQuizzes)} />
            <StatTile label="Average" value={`${stats.averageScore}/10`} />
            <StatTile label="Best" value={`${stats.bestScore}/10`} />
          </div>

          {/* Per topic */}
          {stats.byTopic.length > 0 && (
            <div>
              <h2 className="font-heading font-semibold text-lg mb-3">By topic</h2>
              <div className="space-y-2">
                {stats.byTopic.map((t) => (
                  <div
                    key={t.mathType}
                    className="flex items-center gap-3 p-3 rounded-xl bg-card border border-border"
                  >
                    <span className="text-2xl w-8 text-center">
                      {mathTypeLabels[t.mathType as MathType]?.emoji ?? "❓"}
                    </span>
                    <div className="flex-1">
                      <p className="font-heading font-semibold">
                        {mathTypeLabels[t.mathType as MathType]?.label ?? t.mathType}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {t.quizzes} {t.quizzes === 1 ? "quiz" : "quizzes"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-heading font-bold text-primary">avg {t.averageScore}/10</p>
                      <p className="text-sm text-muted-foreground">best {t.bestScore}/10</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent */}
          <div>
            <h2 className="font-heading font-semibold text-lg mb-3">Recent quizzes</h2>
            <div className="space-y-2">
              {stats.recent.map((r, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-card border border-border">
                  <span className="text-xl w-8 text-center">
                    {r.mathType ? mathTypeLabels[r.mathType as MathType]?.emoji : "🎲"}
                  </span>
                  <div className="flex-1">
                    <p className="font-heading font-semibold">
                      {r.mathType ? mathTypeLabels[r.mathType as MathType]?.label : "Quiz"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {r.grade ? (r.grade === "K" ? "Kindergarten" : `Grade ${r.grade}`) : ""}
                      {r.difficulty ? ` · ${difficultyConfig[r.difficulty as Difficulty].label}` : ""}
                      {` · ⏱ ${r.time}`}
                    </p>
                  </div>
                  <p className="font-heading font-bold text-primary">{r.score}/{r.total}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        onClick={onBack}
        className="mt-8 px-6 py-3 rounded-2xl bg-card border-2 border-border font-heading font-bold hover:border-primary/40 transition-all"
      >
        ← Back
      </motion.button>
    </motion.div>
  );
};

const StatTile = ({ label, value }: { label: string; value: string }) => (
  <div className="p-4 rounded-2xl bg-secondary/10 border-2 border-secondary/40 text-center">
    <p className="text-2xl font-heading font-bold text-primary">{value}</p>
    <p className="text-xs font-heading font-semibold text-muted-foreground mt-1">{label}</p>
  </div>
);

export default ProgressScreen;

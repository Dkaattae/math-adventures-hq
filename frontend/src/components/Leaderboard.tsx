import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { getLeaderboard } from "@/lib/api";

const Leaderboard = () => {
  const { data: leaderboard = [], isLoading, isError } = useQuery({
    queryKey: ["leaderboard"],
    queryFn: () => getLeaderboard({ limit: 5 }),
  });

  if (isLoading) {
    return <p className="text-center text-muted-foreground font-body">Loading leaderboard...</p>;
  }
  if (isError) {
    return null; // leaderboard is a nice-to-have; fail quietly rather than blocking the username screen
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-md mx-auto"
    >
      <h2 className="text-2xl font-heading font-bold text-center mb-4 flex items-center justify-center gap-2">
        🏆 Leaderboard
      </h2>
      <div className="space-y-2">
        {leaderboard.map((entry, i) => (
          <motion.div
            key={entry.name}
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
            <div className="flex-1">
              <p className="font-heading font-semibold">{entry.name}</p>
              <p className="text-sm text-muted-foreground">⏱ {entry.time}</p>
            </div>
            <div className="text-right">
              <p className="font-heading font-bold text-primary">
                {entry.score}/{entry.total}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

export default Leaderboard;

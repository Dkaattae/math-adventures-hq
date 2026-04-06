import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { existingUsernames } from "@/data/mockData";
import Leaderboard from "./Leaderboard";

interface Props {
  onSubmit: (name: string) => void;
}

const UsernameScreen = ({ onSubmit }: Props) => {
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    if (existingUsernames.some((u) => u.toLowerCase() === trimmed.toLowerCase())) {
      setError("Oops! That name is taken. Try adding your last name or a lucky number 😊");
      return;
    }
    setError("");
    onSubmit(trimmed);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen flex flex-col items-center justify-center p-6 gap-10"
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", bounce: 0.5 }}
        className="text-center"
      >
        <h1 className="text-5xl md:text-6xl font-heading font-bold mb-2">
          🎓 MathQuest
        </h1>
        <p className="text-lg text-muted-foreground font-body">
          The fun way to practice math!
        </p>
      </motion.div>

      <motion.div
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="w-full max-w-sm space-y-4"
      >
        <div className="space-y-2">
          <label className="font-heading font-semibold text-lg">
            What's your name? 👋
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setError(""); }}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Type your name here..."
            className="w-full px-5 py-4 text-lg rounded-2xl border-2 border-border bg-card font-body focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/30 transition-all"
          />
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="text-destructive text-sm font-body"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={handleSubmit}
          disabled={!name.trim()}
          className="w-full py-4 rounded-2xl bg-primary text-primary-foreground font-heading font-bold text-lg shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:shadow-xl"
        >
          Let's Go! 🚀
        </motion.button>
      </motion.div>

      <Leaderboard />
    </motion.div>
  );
};

export default UsernameScreen;

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ApiError, checkUsername, createUser, login } from "@/lib/api";
import Leaderboard from "./Leaderboard";

interface Props {
  onSubmit: (name: string) => void;
}

// Two-step: type a name (we detect new vs returning), then set or enter a PIN.
type Mode = "new" | "returning" | null;

const UsernameScreen = ({ onSubmit }: Props) => {
  const [name, setName] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [mode, setMode] = useState<Mode>(null);
  const checkSeq = useRef(0);

  // Debounced availability lookup: decides whether to ask the kid to
  // create a PIN (new name) or enter theirs (returning name).
  useEffect(() => {
    const trimmed = name.trim();
    setMode(null);
    setPin("");
    setError("");
    if (!trimmed) return;
    const seq = ++checkSeq.current;
    const t = setTimeout(async () => {
      try {
        const res = await checkUsername(trimmed);
        if (checkSeq.current === seq) setMode(res.available ? "new" : "returning");
      } catch {
        // Hint is decorative — stay quiet if the lookup fails.
      }
    }, 400);
    return () => clearTimeout(t);
  }, [name]);

  const handleSubmit = async () => {
    const trimmed = name.trim();
    if (!trimmed || submitting) return;
    if (mode && pin.length !== 4) {
      setError("Your PIN needs to be 4 digits 🔢");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      if (mode === "returning") {
        await login(trimmed, pin);
      } else {
        await createUser(trimmed, pin);
      }
      onSubmit(trimmed);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("That PIN doesn't match. Try again! 🔑");
      } else if (err instanceof ApiError && err.status === 409) {
        // Raced with another signup — switch to login.
        setMode("returning");
        setError("That name was just taken — enter its PIN to log in.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Names are up to 20 characters and PINs are 4 digits. ✂️");
      } else {
        setError("Couldn't reach the server. Please try again 🔌");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit = name.trim() !== "" && (mode === null || pin.length === 4) && !submitting;
  const buttonLabel = submitting
    ? "Just a sec..."
    : mode === "returning"
      ? "Log in 🔑"
      : "Let's Go! 🚀";

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
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Type your name here..."
            maxLength={20}
            className="w-full px-5 py-4 text-lg rounded-2xl border-2 border-border bg-card font-body focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/30 transition-all"
          />

          <AnimatePresence>
            {mode && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-1 overflow-hidden"
              >
                <label className="font-heading font-semibold text-sm">
                  {mode === "returning"
                    ? `Welcome back, ${name.trim()}! Enter your PIN 🔑`
                    : "Pick a secret 4-digit PIN 🔒"}
                </label>
                <input
                  type="password"
                  inputMode="numeric"
                  autoComplete="off"
                  value={pin}
                  onChange={(e) => { setPin(e.target.value.replace(/\D/g, "").slice(0, 4)); setError(""); }}
                  onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                  placeholder="••••"
                  className="w-full px-5 py-4 text-2xl tracking-[0.5em] text-center rounded-2xl border-2 border-border bg-card font-heading focus:outline-none focus:border-primary focus:ring-2 focus:ring-ring/30 transition-all"
                />
                {mode === "new" && (
                  <p className="text-xs text-muted-foreground font-body">
                    You'll use this PIN to log back in and keep your scores.
                  </p>
                )}
              </motion.div>
            )}
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
          disabled={!canSubmit}
          className="w-full py-4 rounded-2xl bg-primary text-primary-foreground font-heading font-bold text-lg shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:shadow-xl"
        >
          {buttonLabel}
        </motion.button>
      </motion.div>

      <Leaderboard />
    </motion.div>
  );
};

export default UsernameScreen;

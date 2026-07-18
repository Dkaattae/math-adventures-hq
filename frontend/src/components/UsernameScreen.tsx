import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ApiError, checkUsername, createUser, login, resetPin } from "@/lib/api";
import Leaderboard from "./Leaderboard";

interface Props {
  onSubmit: (name: string) => void;
}

// Two-step: type a name (we detect new vs returning), then set or enter a
// PIN. A returning player who forgot their PIN can use the rescue code
// from signup; a brand-new player is shown that code once, right here.
type Mode = "new" | "returning" | null;

const UsernameScreen = ({ onSubmit }: Props) => {
  const [name, setName] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [mode, setMode] = useState<Mode>(null);
  // Forgot-PIN recovery state.
  const [forgot, setForgot] = useState(false);
  const [rescueInput, setRescueInput] = useState("");
  // Set right after signup: show the one-time rescue code before entering.
  const [issuedCode, setIssuedCode] = useState<string | null>(null);
  const checkSeq = useRef(0);

  // Debounced availability lookup: decides whether to ask the kid to
  // create a PIN (new name) or enter theirs (returning name).
  useEffect(() => {
    const trimmed = name.trim();
    setMode(null);
    setPin("");
    setForgot(false);
    setRescueInput("");
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

  const fail = (err: unknown) => {
    if (err instanceof ApiError && err.status === 429) {
      setError(err.message); // server's friendly "take a break" message
    } else if (err instanceof ApiError && err.status === 401) {
      setError(
        forgot
          ? "That rescue code doesn't match. Check your note and try again! 📝"
          : "That PIN doesn't match. Try again! 🔑",
      );
    } else if (err instanceof ApiError && err.status === 409) {
      setMode("returning");
      setError("That name was just taken — enter its PIN to log in.");
    } else if (err instanceof ApiError && err.status === 422) {
      setError("Names are up to 20 characters and PINs are 4 digits. ✂️");
    } else {
      setError("Couldn't reach the server. Please try again 🔌");
    }
  };

  const handleSubmit = async () => {
    const trimmed = name.trim();
    if (!trimmed || submitting) return;
    if (mode && pin.length !== 4) {
      setError("Your PIN needs to be 4 digits 🔢");
      return;
    }
    if (forgot && !rescueInput.trim()) {
      setError("Type the rescue code you saved at signup 📝");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      if (forgot) {
        await resetPin(trimmed, rescueInput, pin);
        onSubmit(trimmed);
      } else if (mode === "returning") {
        await login(trimmed, pin);
        onSubmit(trimmed);
      } else {
        const created = await createUser(trimmed, pin);
        // Show the one-time rescue code before entering the app.
        setIssuedCode(created.recoveryCode);
      }
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit =
    name.trim() !== "" &&
    (mode === null || pin.length === 4) &&
    (!forgot || rescueInput.trim() !== "") &&
    !submitting;

  const buttonLabel = submitting
    ? "Just a sec..."
    : forgot
      ? "Set new PIN 🔧"
      : mode === "returning"
        ? "Log in 🔑"
        : "Let's Go! 🚀";

  // Post-signup interstitial: the rescue code, shown exactly once.
  if (issuedCode) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen flex flex-col items-center justify-center p-6"
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", bounce: 0.4 }}
          className="w-full max-w-sm p-6 rounded-3xl border-2 border-secondary/60 bg-secondary/10 text-center space-y-4"
        >
          <p className="text-4xl">🗝️</p>
          <h2 className="text-xl font-heading font-bold">Your secret rescue code</h2>
          <p className="text-2xl font-heading font-bold tracking-wide bg-card border-2 border-border rounded-2xl py-3">
            {issuedCode}
          </p>
          <p className="text-sm text-muted-foreground font-body">
            Write it down somewhere safe! If you ever forget your PIN, this
            code is the only way to get back in — we can't show it again.
          </p>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onSubmit(name.trim())}
            className="w-full py-4 rounded-2xl bg-primary text-primary-foreground font-heading font-bold text-lg shadow-lg"
          >
            I wrote it down — let's go! 🚀
          </motion.button>
        </motion.div>
      </motion.div>
    );
  }

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
                className="space-y-2 overflow-hidden"
              >
                {forgot && (
                  <div className="space-y-1">
                    <label className="font-heading font-semibold text-sm">
                      Your rescue code from signup 🗝️
                    </label>
                    <input
                      type="text"
                      value={rescueInput}
                      onChange={(e) => { setRescueInput(e.target.value); setError(""); }}
                      onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                      placeholder="gold-otter-731"
                      className="w-full px-5 py-3 text-lg text-center rounded-2xl border-2 border-border bg-card font-heading focus:outline-none focus:border-primary transition-all"
                    />
                  </div>
                )}
                <label className="font-heading font-semibold text-sm block">
                  {forgot
                    ? "Pick a new 4-digit PIN 🔒"
                    : mode === "returning"
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
                {mode === "new" && !forgot && (
                  <p className="text-xs text-muted-foreground font-body">
                    You'll use this PIN to log back in and keep your scores.
                  </p>
                )}
                {mode === "returning" && (
                  <button
                    type="button"
                    onClick={() => { setForgot(!forgot); setError(""); }}
                    className="text-sm font-body text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
                  >
                    {forgot ? "← Back to PIN login" : "Forgot your PIN?"}
                  </button>
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

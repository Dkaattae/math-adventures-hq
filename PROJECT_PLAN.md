# Math Adventures HQ — Project Plan

_Last updated: 2026-07-18_

This document collects the roadmap for expanding the quiz, the known bugs
and rough edges found while auditing the codebase, the testing gaps, and
general improvement ideas — roughly in the order they're worth tackling.
Completed work moves to the **Done** section at the bottom.

---

## 1. Expanding the quiz

### Long term

- Printable worksheet export (the generators already produce clean
  question/answer pairs).
- Practice mode (untimed) vs. challenge mode (streaks; the `badge` field
  already exists end to end).
- More visual questions: extend the SVG figures beyond shape ID to
  angles, symmetry, and simple area/perimeter diagrams.

---

## 2. Known bugs & issues

From the 2026-07-15 audit; items are struck off as they land (see Done).
Remaining, ordered by impact:

1. **Stats/suggested-level endpoints are unauthenticated.** Anyone can
   read any player's progress by guessing a username. Low severity for
   this app, but if PINs are meant to "own" a name, stats arguably
   should sit behind login too.
2. **Usernames are an open namespace.** Creation is unauthenticated and
   unthrottled, and the charset is unrestricted — someone could squat
   names or fill the users table. Restrict to a sane charset and add a
   creation rate limit. (Login/reset brute-forcing is now covered by the
   per-account lockout.)

---

## 3. UI & UX findings (2026-07-18 review)

A front-end-focused pass, prompted by "the quiz has too many buttons and
I'm not sure what to click." Ordered by impact.

### 3.1 The quiz screen's interaction model — decision

Verified current behavior: the quiz already IS a **review-before-submit**
model. "Submit Answer" only saves locally (nothing reaches the server
until "Finish ✅"), the 📋 Review panel jumps back to any question, and a
revisited answer is pre-filled and editable. The confusion is that the
controls don't communicate this model:

- **"Submit Answer" sounds final but isn't** — and it sits next to
  "Finish ✅", so there are two submit-sounding buttons doing very
  different things.
- **"Next ➡️" silently discards typed input** (`goNext` doesn't save;
  navigation resets the field). Inconsistent with timer expiry, which
  *does* salvage the draft.
- **There is no Back button** — going back requires discovering the
  collapsed Review panel.
- **"Finish ✅" is always visible with no confirmation** — one tap on
  question 2 ends the quiz with 8 blanks.
- Five buttons total (four in multiple-choice) for what is really a
  two-action screen.

**Decision: keep the review-before-submit model** (it matches the
server's grade-once-at-submit anti-cheat design and the kid-friendly
"go back and fix it" behavior) and redesign the controls to express it:

- **← Back / Next →** as the only two persistent buttons; *both* save
  the typed draft before navigating (kills the silent-discard bug and
  the misleading "Submit Answer" label in one move).
- Replace the position-only progress bar, the Flag button, and the
  hidden Review toggle with one **always-visible strip of 10 tappable
  dots** — filled = answered, ring = current. Tap to jump. (Flags add
  nothing once blanks are permanently visible on a 10-question quiz.)
- **Finish becomes contextual**: primary button after question 10 (or
  once all dots are filled); before that, finishing early asks
  "You still have N blank questions — go back, or finish anyway?".
- Multiple-choice keeps tap-to-save-and-advance; same nav strip.

Net result: 2 buttons + dots + a contextual Finish, one honest model.

### 3.2 Other findings

1. **A failed submit throws away the whole quiz.** If `POST
   /quizzes/{id}/submit` fails (network blip), the error screen only
   offers "Back Home" — 10 answers and 3 minutes of work gone. Keep the
   answers in state and offer "Try again" (the quiz is unsubmitted
   server-side, so a retry is safe).
2. **Total-time expiry is a silent rug-pull.** At 0:00 the quiz submits
   itself with no warning. Turn the total timer red/pulsing for the
   last 30 seconds so the auto-submit isn't a surprise.
3. **Mobile keyboard is wrong for most answers.** The answer input is
   `type="text"` with no `inputMode`, so phones show a full keyboard
   for "7 + 5". Most topics are numeric; fractions ("3/4"), comparison
   ("<"), and word answers are not. Backend could tag each question
   with an expected answer kind so the client can pick
   `inputMode="numeric"` vs text.
4. **Setup screen's Start button materializes from nothing.** It only
   renders once grade+topic+difficulty are all chosen; before that
   there's no hint anything is missing. Always show it, disabled, with
   a "pick a grade / topic / difficulty" nudge.
5. **Leaderboard rows hide their context.** Unfiltered, a "10/10 —
   1m 20s" row doesn't say it was K-easy vs G5-hard. Add small
   grade/topic chips per row.
6. **Rescue-code interstitial has no copy button.** A parent can't tap
   to copy `gold-otter-731` into their notes app.
7. **Accessibility pass needed.** State is color-only in several places
   (green = answered on review dots, red pulse on the timer); buttons
   lean on emoji; the dots need aria-labels ("Question 3, answered").
   Also worth a once-over with keyboard-only navigation.
8. **No way out of a quiz.** Once started, the only exits are Finish
   (which submits) or waiting out the clock. Consider a small "quit"
   with confirmation that discards the attempt.

---

## 4. Testing gaps

### Backend

- **API-level coverage for new types.** Existing tests call
  `generate_questions()` directly; only `addition` is exercised through
  `POST /api/quizzes` → submit. Add a parametrized round-trip test across
  all fourteen `MathType`s.
- **Property-based answer verification.** For every arithmetic factory,
  independently re-evaluate the generated question text and assert it
  equals `correctAnswer` (catches template/answer drift — the class of bug
  most likely to sneak in as factories multiply). `hypothesis` fits well.
  (Regex-based recomputation tests exist for the six newest types; the
  original arithmetic types and a property-based framework are still open.)
- **Leaderboard tie-breaking** — score-desc/time-asc ordering is only
  partially covered.
- **Double-submit race** — the `submitted` flag is checked and set in
  separate steps; two concurrent submits can both pass the check. Needs a
  row-level guard (e.g. conditional UPDATE) and a test.

### Frontend

- **More component tests** — QuizScreen timers/MC, UsernameScreen PIN
  flow, Leaderboard filters, ProgressScreen, and ShapeFigure are covered
  now; still missing: flag/review panel navigation and the ResultsScreen
  recommendation/figure rendering from a `QuizResult` fixture.
- **Flow-level test with a mocked API** (MSW): username → setup → quiz →
  results against canned responses.
- **Automated Playwright smoke test** — the full flow has been verified
  manually with a headless browser; automating it is mostly transcription.

### Infrastructure

- ~~There is no CI~~ — done, see Done section.

---

## 5. Code quality & architecture improvements

- **Generate frontend API types from `openapi.yaml`** (e.g.
  `openapi-typescript`). The contract now lives in three hand-maintained
  copies — `openapi.yaml`, `models.py`, and `frontend/src/lib/api.ts` —
  and each new field (options, figure, pin, stats) has to be added to all
  three by hand; this is exactly how the frontend once drifted onto mock
  data unnoticed.
- **`leaderboard` table is doing double duty** as both the ranking board
  and each user's quiz history (via `query_user_stats`). Consider a
  dedicated history/attempts table, or rename to reflect that it's an
  attempts log the leaderboard reads from.
- **Split `questions.py`** (~1400 lines and growing) into a package:
  `questions/arithmetic.py`, `fractions.py`, `order_of_ops.py`,
  `word_problems.py`, `geometry_data.py`, `distractors.py`, etc., behind
  the same `generate_questions` facade.
- **Tune difficulty scaling per topic.** `_difficulty_range` is linear in
  grade for every type; multiplication should probably cap factors near
  12 (times tables) regardless of range, and fractions difficulty is
  better driven by denominator size than by the shared range.

---

## 6. Suggested order of work

| Phase | Items | Why first |
|---|---|---|
| 1 — UI cleanup | Quiz controls redesign (§3.1); failed-submit retry (§3.2.1); time-warning (§3.2.2) | Directly answers real confusion in the core play loop |
| 2 — hardening | Username namespace (§2.2); stats behind login (§2.1) | Remaining security/robustness gaps from the accounts work |
| 3 — polish | Rest of §3.2 (mobile keyboard, setup nudge, leaderboard chips, copy button, a11y); worksheet export; practice vs. challenge mode; more visual questions | Additive depth on a solid base |

---

## Done

Completed items, newest first.

### 2026-07-18 — per-topic level suggestions

- **`suggest_level` is now topic-aware.** `GET
  /api/users/{name}/suggested-level?mathType=fractions` computes the
  suggestion from that topic's history only, so a kid strong at addition
  no longer starts fractions on hard. A never-played topic gets a fresh
  start (their usual grade, clamped up to the topic's entry grade, at
  easy — `basedOn=0`), and stepping down never suggests a grade below
  the topic's entry grade. The setup screen re-suggests when a topic is
  picked, never overriding a manual grade/difficulty choice, with a
  "first time with this topic — we'll start you off easy!" hint for
  fresh topics. The stats and suggested-level endpoints are now also
  documented in `openapi.yaml` (they'd been missed).

### 2026-07-16 — PIN recovery + login lockout (was §2.1)

- **Rescue codes.** Signup now issues a one-time, kid-friendly rescue
  code (e.g. `gold-otter-731`, ~512k combos) shown once on an
  interstitial ("write it down!"); only its PBKDF2 hash is stored.
  `POST /api/users/reset-pin` sets a new PIN when the code matches, and
  the login screen gained a "Forgot your PIN?" flow.
- **Brute-force lockout.** 5 consecutive failed login *or* reset
  attempts lock the account for 15 minutes (DB-backed:
  `users.failed_attempts` / `users.locked_until`, migration `0002` —
  the first real proof of the Alembic workflow). Locked attempts get a
  429 with `Retry-After` and a friendly message; a successful login
  clears the counter.

### 2026-07-15 — Alembic, unified level logic, deploy guide

- **Alembic migrations replace `create_all`.** Schema is now versioned in
  `backend/migrations/`; the app runs `alembic upgrade head` at startup
  (opt out with `SKIP_MIGRATIONS=1`), so fresh databases get the full
  schema — `pin_hash` included — and future column changes have a home.
  `DATABASE_URL` is also normalized so a pasted Supabase `postgresql://`
  string works with the psycopg driver, and the container binds Railway's
  `$PORT`.
- **Unified the level-recommendation ladder.** One source of truth,
  `app/leveling.py: next_level`, now drives both the end-of-quiz
  recommendation (returned on the quiz-submit response) and the
  returning-player `suggest_level`; the frontend only turns the server's
  decision into text (`recommendationText`), so the two can no longer
  disagree (was bug #4).
- **Deployment guide.** `DEPLOYMENT.md` documents a Railway + Supabase
  single-container deploy end to end.

### 2026-07-15 — depth features

- **PIN accounts.** New players set a 4-digit PIN (PBKDF2-hashed,
  stdlib-only) and returning players enter it to reclaim their name;
  `POST /api/users/login` verifies it. The username screen detects
  new-vs-returning and shows the matching PIN field.
- **Progress view.** `GET /api/users/{name}/stats` aggregates a player's
  attempts (totals, per-topic averages/bests, recent quizzes) from the
  leaderboard rows; a "📊 My Progress" screen renders it.
- **History-based adaptive difficulty.** `GET
  /api/users/{name}/suggested-level` nudges the last-played level up/down
  by recent average score, and the setup screen pre-selects it for
  returning players ("we picked up where you left off").
- **Visual geometry.** Questions can carry a `figure` (shape name); the
  client draws it as an inline SVG (`ShapeFigure`) — computed regular
  polygons plus circle/rectangle. Visual shape-ID questions join the
  EASY geometry tier and appear in geometry and mixed quizzes.
- (Known follow-ups from auditing this work are logged in §2.)

### 2026-07-14 — grade gating + leaderboard filters

- **Grade-appropriate topic gating.** A per-topic minimum grade
  (`_MIN_GRADE_FOR_TYPE` in the backend, `minGradeForType` in
  `quizConfig.ts`, kept in sync) drives two things: the setup screen only
  shows topics unlocked at the chosen grade (with a "more topics unlock"
  hint, and it clears a now-invalid selection when the grade drops), and
  the `mixed` sampler draws only from grade-appropriate topics.
- **Leaderboard filters in the UI.** The home-screen leaderboard gained
  Grade / Topic / Level dropdowns wired to the existing
  `mathType`/`difficulty`/`grade` query params, plus a friendly empty
  state when nothing matches.

### 2026-07-14 — multiple choice, mixed topic, adaptive nudge

- **Multiple-choice mode.** `QuizCreate` takes an `answerMode`; questions
  gain an optional `options` list. Distractors are generated generically
  (near-miss numbers for integers, nearby values for decimals/fractions,
  and same-quiz sibling answers — which covers categorical answers like
  "even"/"odd" or shape names without hardcoded pools). Options are
  never the wrong count and always contain exactly one correct choice
  (both property-tested across all types). The setup screen offers a
  "Type it / Multiple choice" toggle; QuizScreen renders option buttons.
- **Mixed-topic quizzes.** A 🎲 `mixed` MathType samples each of the 10
  questions from a random topic (dedup across types), available in both
  answer modes.
- **Adaptive end-of-quiz nudge.** `recommendNext(grade, difficulty,
  score)` suggests a next level — level up on a high score, ease down on
  a low one, steady practice in between — shown as an encouraging popup
  on the results screen with a one-tap button to start it. This is the
  lightweight, single-score version; full history-based adaptivity is
  still open (see §1).

### 2026-07-14 — remaining audit bugs + CI

- **CI added** (`.github/workflows/ci.yml`): backend pytest — including
  the Postgres integration suite against a `postgres:16` service —
  plus frontend `tsc --noEmit`, `eslint`, `vitest`, and a production
  build, on every PR and push to main.
- **Client-reported quiz time clamped server-side.** `timeUsedSeconds`
  is now capped at the window the server observed between quiz creation
  and submission, so leaderboard times can't claim more elapsed time
  than actually passed. (Pre-existing eslint errors in shadcn
  scaffolding were also fixed so lint could gate CI.)
- **`GET /api/users/check` is no longer dead code** — the username
  screen now does a debounced availability lookup while typing and
  shows "👋 Welcome back!" or "✨ New player!" before the kid submits.
- **sqlite naive datetimes normalized.** A `UTCDateTime` type decorator
  stores UTC and re-attaches tzinfo on read, so aware datetime
  arithmetic (like the time clamp) works identically on Postgres and
  sqlite, and API timestamps always carry an explicit UTC offset.

### 2026-07-13 — quiz timer & returning-player fixes

- **Bug 1 — total quiz timer paused by typing.** Both countdowns are now
  computed from fixed deadline timestamps inside a single long-lived
  interval (`QuizScreen.tsx`), so re-renders can't tear the clock down.
- **Bug 2 — timer expiry on the last question dead-ended the quiz.**
  Expiry on question 10 now auto-finishes and submits.
- **Bug 3 — timer expiry discarded a typed-but-unsubmitted answer.**
  The draft answer is salvaged before advancing (and on auto-finish).
- **Bug 4 — returning players were locked out of their name.** A 409
  from `POST /api/users` is now treated as "welcome back" and the player
  continues under the existing name (no accounts exist, so no auth to
  check). A PIN system remains a long-term item.
- Component tests added for all four fixes (vitest + React Testing
  Library, fake timers): `QuizScreen.test.tsx`, `UsernameScreen.test.tsx`.

### 2026-07-13 — six new question types (PR #3)

- **Word problems, comparison & number sense, money & time, decimal
  arithmetic, percentages, measurement conversions** — the entire
  near-term expansion list, each with grade/difficulty tier gating.
  Money stays in whole cents; decimals are computed in integer
  tenths/hundredths so answers are exact.
- **Bug 7 — strict answer grading.** `grade_answer` now compares numeric
  answers numerically (`0.50`, `.5`, `7.0` accepted); fractions still
  require simplest form; word answers stay case-insensitive.
- **Bug 9 — stale README.** Topic list refreshed (and again with the
  Features section alongside these fixes).
- `grade_answer` table tests for kid-typed formats added.

### 2026-07-12 — question library expansion + real API (PR #1)

- New `fractions` and `order_of_operations` types; two-step algebra
  (`ax + b = c`) at grade 4+ hard.
- Frontend rewired from leftover `mockData.ts` to the real FastAPI
  backend (typed client in `frontend/src/lib/api.ts`); mock data deleted.

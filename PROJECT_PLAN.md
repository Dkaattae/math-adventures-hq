# Math Adventures HQ — Project Plan

_Last updated: 2026-07-15_

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

From the 2026-07-15 audit. Items 2 (Alembic) and 4 (unified level logic)
are now fixed — see Done. Remaining, ordered by impact:

1. **No PIN recovery + no login rate-limiting.** A kid who forgets their
   4-digit PIN is locked out of that name permanently, and `POST
   /api/users/login` has no throttle, so a 4-digit PIN (10k combos) is
   brute-forceable. Given the audience the stakes are low, but a
   "forgot PIN?" path (even a soft reset) and basic rate-limiting are
   worth it. Usernames are also still an open, unauthenticated namespace.
2. **`suggest_level` ignores the topic.** The history-based level
   suggestion looks at the most recent quiz's level regardless of
   subject, so a kid who's strong at addition but new to fractions gets
   the same suggested level for both. It should be per-topic. (Now that
   the ladder is centralized in `app/leveling.py`, this is a small change
   to which rows `suggest_level` averages over.)
3. **Stats/suggested-level endpoints are unauthenticated.** Anyone can
   read any player's progress by guessing a username. Low severity for
   this app, but if PINs are meant to "own" a name, stats arguably
   should sit behind login too.

---

## 3. Testing gaps

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

## 4. Code quality & architecture improvements

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

## 5. Suggested order of work

| Phase | Items | Why first |
|---|---|---|
| 1 — hardening | PIN recovery + login rate-limit (§2.1); stats behind login (§2.3) | Remaining security/robustness gaps from the accounts work |
| 2 — polish | Per-topic level suggestion (§2.2); worksheet export; practice vs. challenge mode; more visual questions | Additive product depth on a solid base |

---

## Done

Completed items, newest first.

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

# Math Adventures HQ — Project Plan

_Last updated: 2026-07-14_

This document collects the roadmap for expanding the quiz, the known bugs
and rough edges found while auditing the codebase, the testing gaps, and
general improvement ideas — roughly in the order they're worth tackling.
Completed work moves to the **Done** section at the bottom.

---

## 1. Expanding the quiz

### Mid term — product features

- **Grade-appropriate type gating in the UI** — `SetupScreen` currently
  offers every type to every grade; algebra/order-of-operations for
  Kindergarten is questionable. Either hide types below a minimum grade or
  map them to gentler variants.
- **Leaderboard filters in the UI** — the API already supports
  `mathType` / `difficulty` / `grade` query params, but the home screen
  shows one global top-5, which mixes K-easy scores with G5-hard scores.
- **Full adaptive difficulty** — the end-of-quiz recommendation (see Done)
  reacts to a single score. A fuller version would track rolling accuracy
  per user/topic (the data already lands in `quiz_results.results_json`)
  and auto-select the starting tier next time.

### Long term

- Visual geometry: the geometry pool is text-only; rendering SVG shapes
  ("how many sides does *this* shape have?") would unlock much better
  questions.
- Printable worksheet export (the generators already produce clean
  question/answer pairs).
- Lightweight accounts (e.g. a 4-digit PIN) so returning players keep an
  identity, plus a parent-facing progress view.
- Practice mode (untimed) vs. challenge mode (streaks; the `badge` field
  already exists end to end).

---

## 2. Known bugs & issues

All items from the original audit are fixed — see Done. New findings go
here.

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

- **More component tests** — QuizScreen timers and UsernameScreen are
  covered now; still missing: flag/review panel navigation, ResultsScreen
  rendering from a `QuizResult` fixture, SetupScreen selection flow.
- **Flow-level test with a mocked API** (MSW): username → setup → quiz →
  results against canned responses.
- **Automated Playwright smoke test** — the full flow has been verified
  manually with a headless browser; automating it is mostly transcription.

### Infrastructure

- ~~There is no CI~~ — done, see Done section.

---

## 4. Code quality & architecture improvements

- **Generate frontend API types from `openapi.yaml`** (e.g.
  `openapi-typescript`). The contract currently lives in three
  hand-maintained copies — `openapi.yaml`, `models.py`, and
  `frontend/src/lib/api.ts` — which is exactly how the frontend drifted
  onto mock data unnoticed.
- **Split `questions.py`** (~1300 lines and growing) into a package:
  `questions/arithmetic.py`, `fractions.py`, `order_of_ops.py`,
  `word_problems.py`, `geometry_data.py`, etc., behind the same
  `generate_questions` facade.
- **Tune difficulty scaling per topic.** `_difficulty_range` is linear in
  grade for every type; multiplication should probably cap factors near
  12 (times tables) regardless of range, and fractions difficulty is
  better driven by denominator size than by the shared range.
- **Alembic migrations** instead of `create_all()` — schema changes
  currently require wiping the database.
- **Harden user creation** — it's an open unauthenticated endpoint;
  rate-limit it and restrict usernames to a sane character set.

---

## 5. Suggested order of work

| Phase | Items | Why first |
|---|---|---|
| 1 — content & fairness | Grade gating in setup; leaderboard filters in UI | Directly visible to kids; makes the leaderboard meaningful |
| 2 — depth | Full adaptive difficulty; progress history; PIN accounts; visual geometry | Builds on data and infrastructure from phase 1 |

---

## Done

Completed items, newest first.

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

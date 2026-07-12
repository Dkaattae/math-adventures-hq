# Math Adventures HQ — Project Plan

_Last updated: 2026-07-12_

This document collects the roadmap for expanding the quiz, the known bugs
and rough edges found while auditing the codebase, the testing gaps, and
general improvement ideas — roughly in the order they're worth tackling.

Context: PR #1 added two new question types (`fractions`,
`order_of_operations`), two-step algebra at grade 4+ hard, and rewired the
frontend from the leftover `mockData.ts` to the real FastAPI backend.
Everything below assumes that work as the baseline.

---

## 1. Expanding the quiz

### Near term — new question types (reuse the existing factory pattern)

Each of these fits the `Factory` pattern in `backend/app/questions.py`
(signature + question text + answer + kid-friendly explanation), so they're
mostly self-contained additions plus a `MathType` enum entry in
`models.py` / `openapi.yaml` / `quizConfig.ts`:

- **Word problems** — wrap existing arithmetic in sentence templates
  ("Maya has 7 stickers and buys 5 more…"). Could be a standalone type or
  a "story mode" toggle that applies to any arithmetic type.
- **Comparison & number sense** — `<`, `>`, `=` between expressions;
  rounding to the nearest 10/100; place value ("What digit is in the tens
  place of 347?"); even/odd; skip counting and sequences ("2, 4, 6, ?").
- **Money & time** — coin/bill totals, making change; reading clocks and
  elapsed time ("How many minutes from 3:15 to 4:00?"). High curriculum
  value for grades 1–3.
- **Decimal arithmetic** (grades 4–5) — add/subtract tenths and
  hundredths; extends the existing `_DECIMAL_CASES` idea.
- **Percentages** (grade 5 hard) — "What is 25% of 40?"; can reuse the
  fraction-of-a-whole machinery.
- **Measurement conversions** — cm↔m, minutes↔hours, etc.

### Mid term — product features

- **Multiple-choice mode** — backend generates plausible distractors
  (off-by-one, swapped-operation results); `QuestionInternal` gains an
  `options` list. Big UX win for younger kids who struggle to type.
- **Mixed-topic quizzes** — an "everything" option that samples across
  factories, weighted by grade.
- **Grade-appropriate type gating in the UI** — `SetupScreen` currently
  offers every type to every grade; algebra/order-of-operations for
  Kindergarten is questionable. Either hide types below a minimum grade or
  map them to gentler variants.
- **Adaptive difficulty** — track rolling accuracy per user/topic (the
  data already lands in `quiz_results.results_json`) and auto-adjust the
  tier instead of asking the kid to self-select.
- **Leaderboard filters in the UI** — the API already supports
  `mathType` / `difficulty` / `grade` query params, but the home screen
  shows one global top-5, which mixes K-easy scores with G5-hard scores.

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

Found while auditing the current code; ordered by user impact.

1. **Total quiz timer can be paused by typing**
   (`frontend/src/components/QuizScreen.tsx`). The 3-minute countdown's
   `useEffect` depends on `finish`, and `finish` is recreated on every
   keystroke (`inputVal` is in its dependency list) — each keystroke tears
   down and recreates the 1-second interval, so continuous typing stops
   the clock. Fix: compute remaining time from a fixed deadline timestamp
   instead of decrementing state, or move the timer into an effect with
   stable dependencies.
2. **Per-question timer expiry on the last question does nothing.**
   `goNext()` no-ops at question 10, so the quiz just sits there until the
   total timer runs out. Expiry on the last question should auto-finish.
3. **Per-question timer expiry discards a typed-but-unsubmitted answer.**
   `goNext()` advances without saving `inputVal` (unlike `finish()`, which
   does salvage it). Save the draft answer before advancing.
4. **Returning players can't come back.** `POST /api/users` returns 409
   for an existing name and the UI tells the kid the name is taken — but
   there are no accounts, so a returning player permanently loses their
   name. Simplest fix given no auth: treat an existing username as
   "welcome back" and continue; better fix: a PIN.
5. **Client-reported quiz time is trusted.** `timeUsedSeconds` comes from
   the browser and the leaderboard ranks by it (score desc, time asc), so
   it's trivially spoofable. The server knows `createdAt` and
   `submittedAt` — clamp the reported time to that window.
6. **`GET /api/users/check` is dead code** — implemented and tested on the
   backend but never called by the frontend. Either use it for live
   availability feedback while typing, or remove it.
7. **Answer grading is strict about formats.** `grade_answer` rejects
   `0.50` for `0.5` and `.5` for `0.5`; kids will hit this. Numeric
   answers should be compared numerically after parsing, keeping the
   "simplest form" requirement only for fractions.
8. **sqlite dev runs return timezone-naive datetimes** while Postgres
   returns aware ones (`DateTime(timezone=True)` is a no-op on sqlite).
   Normalize to UTC in the storage layer if sqlite stays a supported dev
   path.
9. **README is stale** — it lists six topics; there are now eight. Worth a
   pass after each feature lands (this file included).

---

## 3. Testing gaps

### Backend

- **API-level coverage for new types.** Existing tests call
  `generate_questions()` directly; only `addition` is exercised through
  `POST /api/quizzes` → submit. Add a parametrized round-trip test across
  all eight `MathType`s.
- **Property-based answer verification.** For every arithmetic factory,
  independently re-evaluate the generated question text and assert it
  equals `correctAnswer` (catches template/answer drift — the class of bug
  most likely to sneak in as factories multiply). `hypothesis` fits well.
- **`grade_answer` table tests** for the formats kids actually type:
  trailing zeros, leading dots, spaces around `/`, negative numbers.
- **Leaderboard tie-breaking** — score-desc/time-asc ordering is only
  partially covered.
- **Double-submit race** — the `submitted` flag is checked and set in
  separate steps; two concurrent submits can both pass the check. Needs a
  row-level guard (e.g. conditional UPDATE) and a test.

### Frontend

- **Component tests** (React Testing Library is already installed):
  QuizScreen timer behavior (the bugs in §2 would all have been caught),
  flag/review panel navigation, ResultsScreen rendering from a
  `QuizResult` fixture.
- **Flow-level test with a mocked API** (MSW): username → setup → quiz →
  results against canned responses.
- **Automated Playwright smoke test** — the full flow has been verified
  manually with a headless browser; automating it is mostly transcription.

### Infrastructure

- **There is no CI.** Add a GitHub Actions workflow running backend
  `pytest`, frontend `vitest` + `tsc --noEmit` + `eslint` on every PR.
  This is the highest-leverage single item in this document.

---

## 4. Code quality & architecture improvements

- **Generate frontend API types from `openapi.yaml`** (e.g.
  `openapi-typescript`). The contract currently lives in three
  hand-maintained copies — `openapi.yaml`, `models.py`, and
  `frontend/src/lib/api.ts` — which is exactly how the frontend drifted
  onto mock data unnoticed.
- **Split `questions.py`** (~900 lines and growing) into a package:
  `questions/arithmetic.py`, `fractions.py`, `order_of_ops.py`,
  `geometry_data.py`, behind the same `generate_questions` facade.
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
| 1 — quick wins | CI workflow; QuizScreen timer fixes (§2.1–2.3); returning-player flow (§2.4); README refresh | Small, high-impact, unblocks safe iteration on everything else |
| 2 — content & fairness | Word problems; multiple-choice mode; grade gating in setup; leaderboard filters in UI; numeric answer normalization | Directly visible to kids; makes the leaderboard meaningful |
| 3 — depth | Adaptive difficulty; progress history; PIN accounts; visual geometry | Builds on data and infrastructure from phases 1–2 |

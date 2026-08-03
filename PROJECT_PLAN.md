# Math Adventures HQ — Project Plan

_Last updated: 2026-08-03_

This document collects the roadmap for expanding the quiz, the known bugs
and rough edges found while auditing the codebase, the testing gaps, and
general improvement ideas — roughly in the order they're worth tackling.
Completed work moves to the **Done** section at the bottom.

---

## 1. Expanding the quiz

### Long term

- **Every topic is now shape-based.** Word problems (2026-07-28),
  comparison (2026-07-29), and percentages / measurement / money & time
  (2026-07-30) were all rebuilt around question *shapes* that grow with
  the grade rather than just bigger numbers. Arithmetic (addition,
  subtraction, multiplication, division), fractions, order-of-operations
  and algebra stay single-form on purpose — the operation *is* the skill
  there, and difficulty genuinely is the size of the numbers. If any of
  those later feels flat at grade 5, the shape treatment is the template.
- Printable worksheet export (the generators already produce clean
  question/answer pairs).
- Practice mode (untimed) vs. challenge mode (streaks; the `badge` field
  already exists end to end).
- **Compete mode** (asked 2026-07-31; sketched, not scheduled). Racing
  another player is feasible without WebSockets: one answer lands every
  15–60s, so a 2s poll of a match endpoint reads as live, and React Query
  is already in the app. WebSockets would also cost more than they look —
  the container runs one uvicorn process (`Dockerfile:44`), so in-process
  match state breaks the moment Railway runs a second replica, whereas
  polling reads shared Postgres. Three rungs, cheapest first:
  a **computer opponent** (pure front end: a timer that advances with a
  per-question accuracy probability, paced off the existing
  `timeLimitSeconds`); a **ghost race** against a recorded run (needs
  per-question timings stored, which today they aren't — but no lobby, no
  disconnect handling); and **live PvP**, where the cost is not the
  transport but the match model (both players need the *same* ten
  questions, so generation moves up to a `match` row), a room code to pair
  without notifications, a start barrier, and forfeit rules. Note the
  design tension: the app deliberately withholds correctness until
  submit, so a sudden-death "first wrong loses" mode has to grade each
  answer immediately and gives up review-before-submit — while
  score/speed modes keep the current flow and show only the opponent's
  position. Don't split the screen; mirror the existing dot strip.

- **Ghost race** (chosen 2026-07-31 as the compete-mode rung to build).
  Race a *recorded* run instead of a live person: their dots fill on the
  timeline they actually achieved while you play. No lobby, no
  invitations, no start barrier, no disconnect handling, no polling —
  the whole opponent is data fetched once when the quiz starts.

  **Replay the ghost's quiz, don't generate a parallel one.** Quiz rows
  already store `questions_json`, so a challenger can be served the same
  ten questions the ghost answered — which makes the race genuinely
  like-for-like and the scores directly comparable. Generating a fresh
  quiz "at the same level" instead would mean racing someone who
  answered different questions, which is a pace car, not a race.
  `_public_questions` already strips the answer key, so replaying is
  safe by construction.

  **Where ghosts come from.** Not the leaderboard: `LeaderboardRow` has
  no `quiz_id` (see §5 — the table is doing double duty), so a board row
  can't reach the questions that were asked. The path is
  `quiz_results` → `quizzes`, which does carry both the run and its
  question set.

  **When the grade+topic has no history — the fallback ladder.** This is
  the common case early on, and on niche combinations (percentages,
  grade 4, hard) it may never fill. Walk down until something is found,
  and always say which rung was used rather than silently substituting:

  1. **Another player's run at the same grade + topic + difficulty.**
     Prefer recent runs so the pool doesn't fossilize around one kid
     from months ago.
  2. **Your own best run at that level** — "beat your own record". Always
     available after one attempt, and the most motivating of the
     fallbacks rather than the saddest.
  3. **The nearest neighbouring level** — same topic, adjacent difficulty
     first, then ±1 grade. Label it honestly on screen ("Sam's Grade 4
     run"), because a grade-4 ghost on a grade-3 quiz is a different
     question set and the comparison is only indicative.
  4. **The robot pacer** (rung 1 of compete mode), tuned to the level and
     clearly badged as a robot. Never dress it up as a person.

  Rung 4 means the feature never shows an empty screen, which is what
  makes it safe to put a "Race someone" button on the setup screen
  unconditionally.

  **Concerns, in the order they'd bite:**

  - **Per-question timings don't exist yet.** Only `time_used_seconds`
    (the whole quiz) is stored. Without splits a ghost can only move at
    a constant total/10 pace, which looks robotic and is actively unfair
    on a word problem the real kid spent 40 seconds reading. Needs a new
    column (per-question seconds on `quiz_results`) and the client to
    report them — and, like `timeUsedSeconds` today, they're
    client-reported, so they need the same clamping: the splits must sum
    to no more than the server-observed window, or a doctored payload
    creates an unbeatable ghost.
  - **Privacy.** Per-user history was deliberately made private in
    2026-07-20 (session token + `require_self`); only the leaderboard is
    public. A ghost exposes another child's *pace*, which is more than
    the board reveals today. Decide it explicitly: restrict ghosts to
    runs already visible on the public leaderboard, show the same name
    the board shows, and consider an opt-out — don't drift into
    publishing timing data by accident.
  - **Ghost choice is a motivation lever, not a query detail.** Always
    racing the fastest run on the board means always losing. Pick a
    ghost a little better than the challenger's own recent average — a
    stretch, not a wall. This decides whether the feature is fun or
    quietly discouraging.
  - **Winning has to mean score first, then time**, matching the
    leaderboard ordering. If it's pure speed, blasting through with
    wrong answers wins, which teaches exactly the wrong lesson.
  - **Replay makes questions repeatable.** A kid can race the same ghost
    repeatedly, memorise the ten answers, and post a very fast time.
    Either mark race attempts so they don't write leaderboard rows, or
    accept it and let the board be for fresh quizzes only.
  - **The ghost must never touch the live player's clock.** Per-question
    budgets already auto-advance; the ghost is a display overlay, and if
    it lags or finishes early nothing about the real quiz changes.
  - **Quitting already does the right thing** — abandoned attempts are
    never submitted, so they can't become ghosts. Nothing to add.
- ~~More visual questions~~ — done 2026-07-30: angles, symmetry and
  labelled perimeter/area rectangles, on the same grade ladder as the
  text questions. Still open beyond that: composite figures, angle
  arithmetic on a diagram, and coordinate grids.

---

## 2. Known bugs & issues

**Empty.** Every item from the 2026-07-15 audit has landed, and the four
found in play on 2026-08-03 — repeated questions from two different
causes, and two multiple-choice faults — shipped the same day; see Done.
New findings go here as they're spotted.

---

## 3. UI & UX findings (2026-07-18 review)

A front-end-focused pass, prompted by "the quiz has too many buttons and
I'm not sure what to click." The quiz controls redesign and failed-submit
retry shipped 2026-07-19; the total-time warning, mobile keyboard and
setup-screen Start button shipped 2026-07-24; the leaderboard row chips
and the quiz exit shipped 2026-07-30 (see Done). Remaining findings,
ordered by impact:

1. **Rescue-code interstitial has no copy button.** A parent can't tap
   to copy `gold-otter-731` into their notes app.
2. **Accessibility pass needed.** The dot strip ships with aria-labels,
   the two timer warnings say their state in words, and the quit dialog
   is a labelled `role="dialog"`, but the rest of the app deserves a
   keyboard-only + screen-reader once-over (buttons lean on emoji; focus
   order is unverified, and the quit dialog doesn't trap focus or close
   on Escape).

---

## 4. Testing gaps

### Backend

**All clear as of 2026-07-31** — the four items below have landed and the
remaining gaps are all front-end. Two of the four turned up a real fix,
not just missing coverage.

- ~~**API-level coverage for new types**~~ — done 2026-07-31.
  `test_api_all_topics.py` drives all fifteen `MathType`s (including
  `mixed`) through `POST /api/quizzes` → submit, at each topic's entry
  grade and at grade 5, in both answer modes: creation shape, no answer
  key on the wire, four distinct options that a tap can actually grade,
  a perfect run, a zero run, and the leaderboard + history rows a
  finished quiz leaves behind.
- ~~**Property-based answer verification**~~ — done 2026-07-30. Every
  question printed by the eight arithmetic topics is parsed and re-solved
  by `test_answer_verification.py`, which shares no code with the
  generators (precedence comes from Python's own `ast`). What's left is
  the topics that can't be re-solved from text alone — word problems,
  measurement, money & time, percentages — which keep their existing
  per-shape recomputation instead.
- ~~**Leaderboard tie-breaking**~~ — done 2026-07-30, and it needed a fix
  as well as tests: ordering had no third key, so rows tied on score
  *and* time came back in whatever order the database chose. Earliest
  achievement now wins the tie.
- ~~**Double-submit race**~~ — done 2026-07-31. `mark_submitted` now
  claims the quiz with `UPDATE ... WHERE submitted = false` and returns
  whether it won; the loser gets the same 409 the early check raises.
  What the race actually did before the fix was slightly different from
  the guess above: `quiz_results.quiz_id` is a primary key, so the
  database *did* stop the second result row — but by raising
  `IntegrityError` out of the endpoint as a 500, and only because of
  that constraint rather than by intent. `test_double_submit.py` drives
  the interleaving deliberately (a rival submit commits on its own
  session mid-grading) instead of hoping threads collide.

### Frontend

- **More component tests** — QuizScreen timers/MC/navigation (dot strip,
  draft-saving Back/Next, blank-check confirm, quit), UsernameScreen PIN flow,
  Index submit-retry, session-token handling in the API client, the
  total-time warning and per-question `inputMode`, the setup screen's
  Start/nudge states, Leaderboard filters, ProgressScreen, and
  ShapeFigure are covered now; still missing: ResultsScreen
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
  attempts log the leaderboard reads from. The ghost race in §1 gives
  this a concrete cost: `LeaderboardRow` carries no `quiz_id`, so a
  board row can't reach the questions that were asked, and the "recent
  quizzes" list on the progress screen (which reads the same table)
  can't either. Ghosts have to come from `quiz_results` instead, which
  means the board and the attempts log answer different questions about
  the same run — exactly the confusion this item is about.
- **Split `questions.py`** into a package:
  `questions/arithmetic.py`, `fractions.py`, `order_of_ops.py`,
  `comparison.py`, `geometry_data.py`, etc., behind
  the same `generate_questions` facade. Seven modules are already
  out — `word_problems.py`, `percentages.py`, `measurement.py`,
  `money_time.py`, `distractors.py`, `question_times.py`, plus the
  shared `rotation.py` — which has pulled the
  file back under ~1400 lines and shows the shape of the rest.
  Comparison (still inline, ~250 lines) is the obvious next lift.
- **Tune difficulty scaling per topic.** `_difficulty_range` is linear in
  grade for every type; multiplication should probably cap factors near
  12 (times tables) regardless of range, and fractions difficulty is
  better driven by denominator size than by the shared range.

---

## 6. Suggested order of work

| Phase | Items | Why first |
|---|---|---|
| 1 — polish | §3 findings 1–2 (rescue-code copy button, a11y pass) | Small, self-contained UX wins; the app is now functionally and structurally sound |
| 2 — depth | Worksheet export; practice vs. challenge mode; more visual questions (§1) | Additive features on a solid base |
| 3 — internals | Generated API types, `questions.py` split, attempts-table rename, per-topic difficulty tuning (§5) | Pay down as the library keeps growing |

---

## Done

Completed items, newest first.

### 2026-08-03 — repeated questions, and multiple choice that gave itself away

Four faults reported from play, all §2.1.

- **Grade-5 comparison repeated itself.** Not the down-levelling cause
  below — a different one. The top tier could only build `3^4 _ 4!`:
  two bare powers, or a power against a factorial, drawn from 29 power
  pairs and five factorials. The maths was right and the shapes were
  few, so the same question came round within a quiz and across quizzes.
  There are now eight more expression shapes — a power inside ordinary
  arithmetic (`2^4 + 3 × 2 + 8`, the shape asked for), a scaled power
  (`3 × 2^5`), a trimmed one (`5^3 - 40`), two powers added, a factorial
  with arithmetic around it — plus `9 × 7 - 12`, `48 ÷ 6 + 15` and
  `4 × 6 + 3 × 5` at grade 4, where every comparison used to be
  `x × y + z`. Measured over 300 quizzes per level: quizzes containing a
  repeat went from 2/200 to 0/300, and grade-5-hard now draws 2,930
  distinct questions per 4,000 (it was far tighter). Comparison
  signatures are also sorted now, so "A _ B" and "B _ A" count as the
  same question — they read as a repeat even though the answer flips.
- **The level ladder walked topics off their own map.** `next_level`
  stepped the grade down without knowing the topic, so a struggling
  grade-4 percentages player was sent to grade 3, and multiplication
  could reach grade 1 — where the number range is too small for ten
  distinct questions (measured: 3 of 10 at K easy). It now takes the
  topic and stops at that topic's entry grade, holding the level while
  still reporting "down". Difficulty still steps down first, and
  stepping *up* is unaffected.
- **Multiple choice offered answers from the wrong universe.** "8! _ 2^6"
  came with `128 · < · 127 · >`, and "Is 41 even or odd?" with
  `< · 21 · 18 · odd` — in both cases only one option was even the right
  kind of thing, so a kid could score without doing any maths. Options
  are now domain-matched: a comparison offers exactly `<`, `>`, `=`;
  even/odd offers both words; a unit question offers units; a shape
  question offers shapes. Where the question already lists its
  alternatives ("• grams • millimeters • meters", "the biggest: 21, 2 or
  17"), those *are* the options and nothing is invented alongside them.
- **The wrong numbers were the wrong wrong numbers.** "8 minutes is how
  many seconds?" offered `480 · 470 · 479 · 477`. Nothing computes 479,
  so it tested nothing. Numeric distractors are now built from
  misconceptions — a dropped or extra zero, a doubling or halving, a
  round-number guess, transposed digits — with at most one near miss.
  The same question now offers `4800 · 490 · 482`. Single-digit answers
  still use neighbours, because 3 vs 30 isn't a misconception.
- The wrong answers moved to `app/distractors.py` (a module §5 already
  wanted), and `test_distractors.py` pins all of it: no option list may
  contain exactly one option of a different kind from the rest, every
  question in a multiple-choice quiz still gets options, and the
  question's own listed alternatives win. `test_comparison.py` gained
  variety tests, and `test_leveling.py` the topic floor.

### 2026-07-31 — per-question timers moved into a table, and lengthened

- **The clock is now data, not a formula.** Budgets used to be computed
  inside `questions.py` — a 15-second base plus a word count — with no
  way to say "word problems need longer" without editing logic, and no
  way to see all the numbers at once. `app/question_times.py` holds the
  whole map keyed by **topic × grade × difficulty**, plus the four global
  knobs (floor, cap, free-word allowance, seconds per power/factorial).
  A budget is `topic base for the grade + difficulty adjustment +
  reading bonus + thinking bonus`, clamped. `time_limit_seconds()` is now
  a thin wrapper over it, and the table is read at request time, so a
  retune reaches quizzes that were already created but not yet played.
- **Word problems 15s → 30s, comparison 15s → 30s from grade 3.** Both
  were reported as too fast in play. Word problems now start at 30 at
  every level (hard +5), and longer scenes still earn a second per extra
  word on top, so a 60-word grade-5 list lands near 65s. Comparison keeps
  15s at K–2, where it's "which of these numbers is biggest", and gets 30
  from grade 3, where it becomes "work out both sides, then compare";
  powers and factorials add their usual 10s each. Geometry at grades 4–5
  went to 20s, since reading a labelled figure comes before the
  arithmetic. Everything else is unchanged at 15.
- **Mixed quizzes needed a fix to make this work.** Their ten questions
  each come from a different topic, so a word problem in a mixed quiz
  would have been served the `mixed` budget. `QuestionInternal` now
  carries the topic that produced it, stored alongside the question, and
  the API prefers it over the quiz's own. Quizzes stored before this
  fall back to the quiz topic rather than breaking.
- `test_question_times.py` pins the table's shape (every `MathType` must
  appear, so a new topic can't inherit a default nobody chose), the two
  numbers that prompted the change, that the eight one-line arithmetic
  topics still get exactly 15, and — because a table the endpoint doesn't
  read is just a document — the budgets as actually served by
  `POST /api/quizzes`, including a word problem inside a mixed quiz. A
  guard rail test keeps any future edit from pushing a whole quiz past
  12 minutes.

### 2026-07-31 — the backend testing gaps closed, and the fix one of them needed

- **Every topic now runs through the real API, not just the generator.**
  `test_api_all_topics.py` parametrizes all fifteen `MathType`s over
  `POST /api/quizzes` → `submit`, at each topic's entry grade and again
  at grade 5, in both answer modes. It checks the things that only exist
  between the generator and the player: answers that are sometimes ints
  and sometimes strings surviving JSON, the answer key and explanation
  staying off the wire until submission, `answerKind` and
  `timeLimitSeconds` being present and sane, four distinct options per
  multiple-choice question with the correct one among them *formatted so
  a tap grades right*, a perfect run scoring 10 and a nonsense run
  scoring 0, and the leaderboard row + history entry a finished quiz
  leaves behind (including that each row can be found by its own filter).
- **Double submits can't both win.** `mark_submitted` claims the quiz
  with a conditional `UPDATE ... WHERE submitted = false` and reports
  whether it won; the router turns a lost claim into the same 409 the
  early check raises, before writing a leaderboard row. Worth recording
  what the bug actually was, since it wasn't quite what §4 predicted:
  `quiz_results.quiz_id` is a primary key, so the *database* already
  stopped the duplicate result row — but by raising `IntegrityError`
  straight out of the endpoint (a 500 to the player, on a retry that was
  already anxious), and only as a side effect of that constraint rather
  than by design. The tests drive the interleaving on purpose — a rival
  submit commits on its own session while the first request is grading —
  rather than hoping two threads collide, and they fail if the
  conditional update is reverted.
- Writing the coverage turned up one low-severity finding, now §2.1:
  grade gating is advisory, `next_level` can walk a topic below the grade
  it's offered at, and down there the value space is too small for ten
  distinct questions.

### 2026-07-30 — leaderboard context, a way out of a quiz, and answers checked twice

- **Every leaderboard row says what level it was set at** (§3.1). A row
  read "🏆 Emma — 10/10 — 1m 20s", which is only meaningful if you know
  whether that was kindergarten easy or grade 5 hard, and with the
  filters set to All it was every level at once. Each row now carries
  small chips — `G3` · `🍕 Fractions` · `Hard` — and rows written before
  those columns existed simply show none. The list is a real `<ul>`/`<li>`
  now, which is also what lets the tests read one row at a time.
- **A quiz can be left** (§3.4). Finish (which submits) and the expiring
  clock were the only exits, so picking the wrong grade meant sitting
  through ten questions you couldn't read — or deliberately tanking a
  score that then landed on the leaderboard. A quiet `✕` beside the
  timer asks "Leave this quiz? Your answers won't be saved and this quiz
  won't count", and leaving returns to setup still logged in. Nothing is
  submitted, so the attempt never reaches history or the board. The
  confirm sets the same latch `finish` uses, so a countdown that expires
  on the way out can't submit the answers behind you.
- **Every arithmetic question is now solved twice** (§4 testing gap).
  `test_answer_verification.py` parses the question text the app
  actually prints and re-solves it with Python's `ast` and exact
  `Fraction` arithmetic — no shared code with the generators, so
  precedence, sign and simplification all have to agree independently.
  It covers addition, subtraction, multiplication, division, algebra
  (by substituting the claimed x back into the equation), fractions,
  order of operations and decimals — 6 grades × 3 difficulties × 12
  seeds each, ~17k questions per run — plus the arithmetic that surfaces
  in mixed quizzes. `test_no_question_escapes_the_checker`
  fails if a new question shape appears that no checker can parse, so
  the suite can't quietly go vacuous, and four small tests prove the
  checker itself rejects wrong answers. Verified against an injected
  PEMDAS bug — it fails, as it should.
- **Leaderboard ties are no longer arbitrary** (§4 testing gap, and a fix
  it turned up). Ordering was score-desc then time-asc with no third key;
  10/10 in 45 seconds is common at easy, and rows tied on both came back
  in whatever order the database chose — which also made the top-5 cut
  non-deterministic. Earliest achievement now breaks the tie (row id as a
  final key), so holding rank 1 can't be taken away by someone merely
  matching it. `test_leaderboard_ordering.py` re-derives the expected
  order with Python's own sort over seeded score/time pools where ties
  are constant.

### 2026-07-30 — reading scales + visual geometry beyond shape ID

- **Reading load now scales separately from the maths.** A 2nd grader
  used to get the same 4-6 line shopping list as a 4th grader — easier
  arithmetic, same wall of text. Word problems now carry a reading scale
  alongside their maths tier (`word_problems.SCALES`): grades 1-2 read a
  **short** list (3-4 lines) with **no scene-setting noise at all**;
  grades 3-4 keep today's standard; grade 5 above easy reads a **long**
  list (up to ~9 lines) that can include a third, never-mentioned zone
  as pure sifting. Same scenes, same templates — each scale just picks
  more or fewer items from the same pools. Structural distractors (the
  wrong-aisle lines) stay at every scale; that's the puzzle, not noise.
- **Visual geometry grew past "name this shape" — on the same ladder.**
  K-2 keep identification (sides, corners, names). Grades 2-3 read a
  *property* off the figure: lines of symmetry, and "is this angle
  acute, right or obtuse?" drawn as two rays with an arc (deliberately
  unlabelled — printing 120° would answer the question). Grades 4-5
  compute from a figure with labelled sides: perimeter, then area.
  `ShapeFigure` learned two parametric figure strings — `angle:<deg>`
  and `rect:<w>x<h>` — alongside the named shapes, and mixed quizzes
  give the generated visuals a fixed share so they actually appear.
- `test_visual_geometry.py` re-derives every visual answer from the
  figure string itself; the word-problem suite now pins the scale
  ladder (short lists and zero noise at G1-2, longer lists at G5).

### 2026-07-30 — percentages, measurement, money & time became shape-based

- **The last three one-line-template topics got the treatment.** Each
  was a single question form whose only difficulty knob was the size of
  the numbers — grade 5 percentages was "What is 10% of 350?", grade 5
  money was "a sticker costs 70¢ and you pay 100¢". Each is now several
  question *shapes* that a quiz rotates through (via the shared
  `rotation.py`), moving from the plain skill at the entry grade to
  reasoning and real-life multi-step problems higher up.
- **Percentages** (`percentages.py`, 7 shapes): the plain "% of N", then
  running it backwards ("9 of 12 — what percent?", "20% of a number is
  15 — what number?"), then the everyday ones — a discount (price
  *after* the cut, not the saving), a tip (a total that goes *up*), a
  double discount ("50% off, then another 20% off the sale price" — and
  no, that isn't 70% off), and choosing the better of two coupons.
- **Measurement** (`measurement.py`, 9 shapes): plain conversion, then
  picking the right unit for a thing, comparing two measurements written
  in different units, and — the point — problems where converting is
  only step one: cutting a 3 m ribbon into 50 cm pieces, how much juice
  is left after pouring, laps of a track. Containers only ever hold
  something they plausibly could (a jug holds liters, not kilometers).
- **Money & time** (`money_time.py`, 12 shapes): past counting coins to
  the *fewest* coins that make an amount (the skill a till uses) and
  "have you enough?", and past "how long between?" to clock arithmetic
  that lands on a time — what time it finishes, when to leave, total
  duration across the hour. Time answers write like `5:20`; `grade_answer`
  now accepts `05:20` too.
- **US spelling throughout.** The measurement rewrite surfaced that
  `word_problems.py` had crept into UK spelling (metres, litres) in an
  app that otherwise uses dollars, quarters and feet — fixed everywhere.
- `test_topic_depth.py` (40+ cases) pins the tier ladders and
  re-derives every answer independently — brute-forcing the true minimum
  for fewest-coins, recomputing discounts and conversions from the
  question text — so a generator bug can't hide behind its own
  arithmetic. Two older tests that had gone template-specific were
  updated to the new shapes.

### 2026-07-29 — comparison compares expressions, not just numbers

- **Grade 4 was still being asked "which is biggest: 3, 15, 24?"** — a
  grade-2 question. The topic now has five tiers: plain numbers at K-2,
  then from grade 3 both sides of the blank are something to work out
  first.
  - **Grade 3** keeps to `+` but on both sides: `14 + 63 _ 49 + 19`,
    plus "which of these three sums is biggest?".
  - **Grade 4** brings in more operators, so precedence decides the
    answer: `19 + 10 × 7 _ 3 + 6 × 5`. Rounding moves to the nearest
    100, sequences start multiplying (`3, 6, 12, 24, ?`), and the
    biggest-of-three question uses expressions rather than two-digit
    sums.
  - **Grade 5** adds powers, factorials and brackets: `9^4 _ 7!`,
    `2^9 _ 8^3`, `(5 + 14) × 8 _ 15 + 3 × 6`. Both notations come with a
    reminder of what they mean, the same way the word-problem scoring
    scenes state their rules — a fifth grader may never have seen `!`.
    Powers are capped at 10,000 so they stay workable by hand, and a
    handful of secretly-equal pairs (`2^4` / `4^2`) keep `=` reachable.
- **Guessing doesn't pay.** Which side of the comparison goes first is a
  coin flip inside the shared builder, so `<` and `>` each land ~40% of
  the time with `=` making up the rest — measured, and asserted in the
  tests.
- **Shape rotation is now shared.** `app/rotation.py` holds the
  deal-from-a-shuffled-deck helper that word problems introduced; both
  topics use it, so a comparison quiz also covers every shape its tier
  offers before repeating one.
- **Answers are re-derived in the tests.** `test_comparison.py` parses
  each generated expression and evaluates it with a separate
  implementation, so a precedence or factorial bug can't cancel itself
  out — the property-based verification §4 asks for, applied to this
  topic.

### 2026-07-28 — word problems became word problems

- **The scenes carry the difficulty now.** The old topic was one-line
  templates with a name glued on ("Maya has 9 apples and gives 2
  away") — strip the words and the arithmetic was untouched, so a fifth
  grader got a kindergarten task in a longer sentence. `word_problems.py`
  builds a scene instead: a titled list, some facts, and a question that
  needs *part* of it. Every scene carries information the answer doesn't
  need, so choosing the relevant numbers is the skill being practised.
- **Six shapes, not six vocabularies.** The first cut of this rewrite
  had 15 settings over only two structures (filter a list, price a
  list), which still reads as one puzzle in fifteen coats. What makes
  ten questions feel different is shape: short stories (K-1), sifting a
  list (grade 2), prices — total, change, difference, split the bill
  (grade 3+), **scoring rules** ("a touchdown is 6 points, a field goal
  is 3" — stated, because a kid who's never watched football still has
  to be able to answer, with one listed rule always unused), **sale
  offers** where leftovers pay full price, and **two ways to buy the
  same thing** (white peaches $2 each vs yellow peaches 2 for $3 —
  cheapest wins, unless the list names a kind, in which case the bargain
  doesn't apply and careless reading costs the mark).
- **38 settings**: 8 counting lists, 8 priced lists, 12 scoring scenes
  (football, basketball, arcade tickets, recycling deposits, reading
  challenge, house points, scout badges, sports day, funfair tokens,
  board game treasure, chore stars, bird watching) and 10 two-way
  choices. The name pool went from 10 to 40 and appears **once** per
  question instead of three times in one sentence.
- **Rotation, not random draw.** `rotating()` deals from a reshuffled
  deck of shapes, so a 10-question quiz covers every shape its tier
  offers before repeating one: 8-9 distinct question types per quiz,
  measured.
- **Noise is random.** Scene-setting facts appear zero, one or two at a
  time and often not at all — if every question ended in a throwaway
  sentence, ignoring the last sentence would become the trick. Noise
  built into the structure (list lines from the wrong aisle, the unused
  scoring rule) always stays: that's the puzzle, not decoration.
- **Questions carry their own clock.** A five-line shopping list can't be
  read in the 15 seconds a "7 + 5" needs, so `Question.timeLimitSeconds`
  gives 15 for anything up to 25 words and roughly a second per word
  beyond that (capped at 120). The whole-quiz clock is the sum plus 30
  seconds of slack — which is exactly the old 3 minutes for a quiz of
  one-liners, so nothing else changed. The client renders multi-line
  questions with their line breaks and steps the type down.
- **Grading got more forgiving** where the new questions needed it: "$22",
  "22 dollars" and "1,200" now count for 22, 22 and 1200.

### 2026-07-24 — time warning, mobile keyboards, honest Start button (was §3.1–3.3)

- **The quiz no longer ends without warning.** The whole-quiz clock
  turns red and pulses for its last 30 seconds, and — because colour
  alone reaches neither a screen reader nor a kid who can't tell red
  from grey — a `role="status"` line says "Less than 30 seconds left —
  finish up!" in words. The 0:00 auto-submit itself is unchanged.
- **Phones show the right keyboard.** Questions now carry an
  `answerKind` (`integer` / `decimal` / `text`) derived from the correct
  answer rather than the topic, since a topic isn't uniform — division
  alone yields whole numbers, decimals *and* fractions. The client maps
  it to `inputMode`, so "7 + 5" gets a numeric keypad while fractions
  ("3/5"), comparisons ("<"), words and **negative answers** keep the
  full keyboard: phone keypads have no minus or "/" key. The input stays
  `type="text"` so nothing becomes untypable, and the field is derived
  at read time so it can't drift from the answer it describes.
- **The setup screen stops hiding its Start button.** It's always on
  screen, disabled until the form is complete, with a nudge naming
  what's left ("Still to pick: a topic and how tough 👆") that narrows
  as choices are made and gives way to the encouraging message at the
  end. An incomplete form no longer looks finished.

### 2026-07-20 — private progress + username namespace (was §2.1, §2.2)

- **A player's history is now their own.** Signup, login and PIN reset
  hand back a 30-day session token (`sessions` table, migration `0003`;
  only the token's SHA-256 is stored, since 256 random bits need no slow
  KDF). `GET /api/users/{name}/stats` and `/suggested-level` require a
  bearer token whose account matches the name in the path — no token,
  someone else's token, an expired one, or a malformed header all get a
  401. A PIN reset revokes every session issued before it, which is the
  point of a reset. The leaderboard stays public. The frontend keeps the
  token in memory only (a shared family computer shouldn't hold a
  session across reloads) and drops it whenever a player heads Home.
- **Usernames are no longer a free-for-all.** One shared `Username` type
  (letters, digits, spaces, `-`, `_`, `'`; Unicode-aware so "José"
  works; must start with a letter or digit; trimmed, 1–20 chars) now
  guards signup, login, PIN reset, quiz creation and the availability
  check, so markup, control characters and emoji bounce with a 422.
  Signup — the one unauthenticated write — is rate-limited per client IP
  (default 10/hour, `SIGNUP_RATE_LIMIT` / `SIGNUP_RATE_WINDOW_SECONDS`,
  `0` disables) with a 429 + `Retry-After`. Failed attempts count too,
  so hammering one taken name isn't a free pass; logins are untouched so
  a family sharing an IP can still all sign in.

### 2026-07-19 — quiz controls redesign + failed-submit retry (was §3.1, §3.2.1)

- **Quiz controls now express the review-before-submit model.** Five
  buttons became two: ← Back / Next → both save the typed draft (killing
  the silent-discard-on-Next bug and the misleading "Submit Answer"
  label). An always-visible strip of 10 tappable, aria-labeled dots
  (filled = answered, ring = current) replaces the progress bar, the
  Flag button, and the hidden Review panel. Finish only appears on the
  last question or once everything is answered, and finishing with
  blanks asks "You still have N blank questions!" with a "Keep going"
  that jumps to the first blank; the live draft counts as answered in
  the check. Multiple-choice keeps tap-to-save-and-advance.
- **A failed submit no longer loses the quiz.** The answers stay in
  state and the error screen offers "🔄 Try again", resubmitting the
  identical payload (safe — the quiz is unsubmitted server-side). An
  `already_submitted` 409 gets a no-retry message instead of a loop,
  and starting a new quiz clears any stale pending submission.

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

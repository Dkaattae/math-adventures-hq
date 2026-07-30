# Math Adventures HQ

A kids' math quiz web app. Players pick a grade (K–5), a math topic, a
difficulty, and how they want to answer, then take 10 auto-generated
questions against the clock. Scores are persisted to a Postgres-backed
leaderboard.

## Features

- **14 math topics + a Mixed mode**: addition, subtraction,
  multiplication, division, algebra, geometry, fractions, order of
  operations, word problems, comparing numbers, money & time, decimals,
  percentages, and measurement conversions — plus a 🎲 Mixed option that
  samples across all of them in one quiz.
- **Two answer modes**: type the answer, or pick from multiple choice.
  Distractors are generated per question (off-by-one near-misses plus
  same-topic decoys), so multiple choice works for every topic.
- **Grade & difficulty tiers**: every topic scales with grade (K–5) and
  difficulty (easy/medium/hard) — e.g. division introduces remainders at
  grade 3 medium and fractions/decimals at grade 5 hard.
- **Word problems that are actually word problems**: instead of "Maya has
  9 apples and gives 2 away", these build a scene that carries facts the
  answer doesn't need. Six question *shapes* — not just six vocabularies
  — across 38 settings, and a quiz deals through them so ten questions
  never share one skeleton:
  - **sift a list** — which of these belong in the produce aisle?
  - **prices** — quantity × price, then a total, change, or a split bill
  - **scoring rules** — "a touchdown is 6 points, a field goal is 3",
    then what the score sheet says (the rules are spelled out, so a kid
    who's never watched football can still answer, and one listed rule
    is always a red herring)
  - **sale offers** — "$3 each, or 2 for $5", where leftovers pay full
    price
  - **two ways to buy** — white peaches at $2 each or yellow peaches 2
    for $3: which works out cheaper? And if the list says *white*
    peaches, the bargain doesn't apply
  - **short stories** for K–1, where the reading is the hard part
  Scene-setting noise appears only *sometimes*, so "ignore the last
  sentence" never becomes the trick.
- **Comparison that grows up**: K–2 compares plain numbers, but from
  grade 3 both sides of the blank are something to work out first —
  `14 + 63 _ 49 + 19` at grade 3 (still only `+`), then mixed operators
  where precedence decides it (`19 + 10 × 7 _ 3 + 6 × 5`), then powers,
  factorials and brackets at grade 5 (`9^4 _ 7!`, with a reminder of
  what `!` and `^` mean). Which side goes first is a coin flip, so
  guessing `<` every time never pays.
- **Percentages, measurement and money & time that scale**: each is
  several question shapes a quiz rotates through, not one template with
  bigger numbers. Percentages go from "% of N" to discounts, tips and
  double-discount sales ("50% off, then another 20% off — not 70%").
  Measurement moves from a plain conversion to two-step problems
  (cutting a 3 m ribbon into 50 cm pieces). Money & time reaches the
  *fewest* coins that make an amount and clock arithmetic that lands on
  a time ("leaves at 11:10, journey 70 min — when to set off?").
- **Reading scales with the reader**: the maths tier and the reading
  load are separate knobs. Grades 1–2 get short lists with no
  scene-setting noise; grades 3–4 the standard scene; grade 5 longer
  lists with an extra distractor section. Same templates throughout —
  each level just draws more or fewer lines from the same scenes.
- **Grade-appropriate topics**: the setup screen only offers topics that
  fit the chosen grade (no long division for Kindergarteners), and the
  🎲 Mixed quiz samples only from unlocked topics.
- **Filterable leaderboard**: narrow the leaderboard by grade, topic, and
  difficulty so a K-easy run isn't ranked against a Grade-5-hard one.
- **Adaptive difficulty**: at the end of a quiz the app suggests a next
  level (up when a kid aces it, down when they struggle) with a one-tap
  button, and returning players' setup screen pre-selects a level from
  their recent history — per topic, so being great at addition doesn't
  start fractions on hard.
- **Timed quizzes**: 15 seconds for a one-line question, more for a
  word-problem scene that has to be read (the whole-quiz clock is the sum
  of its questions plus a little slack). A tappable
  dot strip shows which questions are answered and jumps anywhere; Back
  and Next keep your typed answer, and finishing with blanks asks first.
  The last 30 seconds are flagged in colour *and* words before the quiz
  auto-submits. A quiz can also be left: the `✕` beside the timer asks to
  confirm and then discards the attempt — nothing is submitted, so a
  wrong-level start never lands on the leaderboard.
- **Right keyboard on phones**: each question reports whether its answer
  is a whole number, a decimal, or free text, so numeric questions bring
  up a keypad while fractions, `<`/`>` and word answers keep the full
  keyboard.
- **Forgiving answer grading**: numeric answers are compared as numbers
  (`0.50` counts for `0.5`), fractions require simplest form by design,
  word answers are case-insensitive.
- **Anti-cheat by design**: the API never reveals correct answers (or
  which option is right) until the quiz is submitted; grading happens
  server-side, and reported quiz time is clamped to the server-observed
  window.
- **PIN accounts**: new players pick a 4-digit PIN (PBKDF2-hashed) and
  returning players enter it to reclaim their name and scores. Signup
  issues a one-time rescue code (e.g. `gold-otter-731`) for forgotten
  PINs, and 5 failed attempts lock the account for 15 minutes. Names are
  limited to letters, digits, spaces, `-`, `_` and `'`, and signups are
  rate-limited per client so the namespace can't be squatted.
- **Private progress**: logging in issues a 30-day session token, and a
  player's own history (progress + suggested level) is only readable with
  it. The leaderboard stays public.
- **Progress view**: a "My Progress" screen shows totals, per-topic
  averages and bests, and recent quizzes.
- **Visual geometry on a ladder**: K–2 identify the drawn shape; grades
  2–3 read a property off it (lines of symmetry, "is this angle acute,
  right or obtuse?" — the angle is drawn, not named); grades 4–5 compute
  perimeter and area from a rectangle with labelled sides.
- **Leaderboard**: score + time ranking with Grade / Topic / Level
  filters right on the home screen, and each row labelled with the level
  it was set at (`G3` · `🍕 Fractions` · `Hard`). Ties on both score and
  time go to whoever got there first, so a rank can't be taken by a run
  that merely matches it.
- **Kid-friendly explanations**: every question carries a short "here's
  how" hint with the graded results.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Vite + React + TypeScript, Tailwind, shadcn/ui |
| Backend | FastAPI, SQLAlchemy 2.x, psycopg v3 |
| Database | Postgres 16 |
| Packaging | Single multi-stage Dockerfile serves the built SPA from FastAPI |
| Dev runner | `concurrently` runs vite + uvicorn together |

## Repo layout

```
.
├── frontend/          # Vite/React app
├── backend/           # FastAPI + SQLAlchemy + tests
│   └── app/
│       ├── main.py          # app entrypoint + SPA static mount
│       ├── db.py            # SQLAlchemy engine factory
│       ├── db_models.py     # ORM models
│       ├── models.py        # Pydantic schemas (match openapi.yaml)
│       ├── questions.py     # per-type question generators + dedup
│       ├── word_problems.py # real-life scenes for the word problems
│       ├── percentages.py  # discount / tip / backwards percentage shapes
│       ├── measurement.py  # conversions + convert-then-solve shapes
│       ├── money_time.py   # coins, fewest-coins, clock arithmetic
│       ├── rotation.py     # deal question shapes from a shuffled deck
│       ├── storage.py       # DB-backed repository
│       └── routers/         # users / quizzes / leaderboard
├── Dockerfile         # multi-stage: vite build -> python runtime
├── docker-compose.yml # postgres + app (only port 8000 published)
├── openapi.yaml       # API contract
└── package.json       # root dev runner (concurrently)
```

## Quick start — Docker Compose (one command)

This is the easiest way to see the whole thing running.

```bash
docker compose up -d --build
# open http://localhost:8000
```

- `GET /` serves the built React SPA
- `GET /api/leaderboard` returns live leaderboard rows
- Postgres is **not** published to the host — only the `app` container
  reaches it over the internal compose network

Stop it with `docker compose down`, or `docker compose down -v` to also
wipe the Postgres volume.

## Deploying

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for a step-by-step guide to
deploying on **Railway** (single container) with a **Supabase** Postgres
database. Schema is managed by Alembic and applied automatically on
startup.

## Local development (hot reload)

Two processes with HMR: Vite on `:8080`, FastAPI on `:8000`, with Vite
proxying `/api/*` and `/healthz` through to the backend.

```bash
# one-time setup
docker compose up -d postgres        # start just Postgres
cd frontend && npm install && cd ..  # install frontend deps
cd backend && pip install -r requirements.txt && cd ..
npm install                          # installs concurrently at the root

# run both processes
export DATABASE_URL="postgresql+psycopg://math:math@localhost:5432/math_adventures"
# (only needed if you're hitting Postgres from the host)
npm run dev
# open http://localhost:8080
```

If you want host access to Postgres during dev (e.g. for `psql`), add
`ports: ["5432:5432"]` under the `postgres` service in
`docker-compose.yml`.

## Running tests

```bash
# everything
npm test

# frontend only (vitest)
cd frontend && npm test

# backend only (pytest)
cd backend && python -m pytest -q
```

Backend unit tests use SQLite in-memory (fast, no Docker needed). A
separate live Postgres integration suite
(`backend/tests/test_postgres_integration.py`) runs automatically if
Postgres is reachable at `localhost:5432`, otherwise it auto-skips. To
run it against the compose Postgres without publishing the port:

```bash
docker compose exec -e INTEGRATION_DATABASE_URL="postgresql+psycopg://math:math@postgres:5432/math_adventures" \
  app sh -c "pip install -q pytest httpx && cd /app/backend && python -m pytest tests/test_postgres_integration.py -q"
```

## Environment variables

The backend reads a single env var:

| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://math:math@localhost:5432/math_adventures` | SQLAlchemy URL. A bare `postgresql://` (or Supabase's `postgres://`) is rewritten to the psycopg v3 driver automatically. |
| `FRONTEND_DIST` | `/app/frontend_dist` | Where main.py looks for the built SPA; set by the Dockerfile. Leave unset in dev. |
| `SKIP_MIGRATIONS` | unset | Set to `1` to skip `alembic upgrade head` at startup. |
| `SIGNUP_RATE_LIMIT` | `10` | Max signups per client per window. `0` disables the limit — raise it for a classroom behind one IP. |
| `SIGNUP_RATE_WINDOW_SECONDS` | `3600` | Window the signup limit is measured over. |

No secrets required. The dev-only Postgres password in
`docker-compose.yml` is safe to commit because the service isn't exposed.

## Deploying to the cloud

The entire app ships as **one Docker image** — frontend is baked in and
served by FastAPI — so any platform that can run a Dockerfile + provision
a Postgres instance will work.

### Railway (recommended, simplest)

1. **Create a new project** from this repo on [railway.app](https://railway.app).
   Railway auto-detects the `Dockerfile` at the repo root.

2. **Add a Postgres plugin** to the same project: *New → Database → Add PostgreSQL*.
   Railway creates a managed Postgres and exposes variables like `PGUSER`,
   `PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE`, `DATABASE_URL`.

3. **Set the app's `DATABASE_URL` variable** to use the `postgresql+psycopg`
   scheme. Railway's default `DATABASE_URL` uses `postgresql://`, which
   SQLAlchemy maps to psycopg2 (not installed). In your service's
   *Variables* tab, add:

   ```
   DATABASE_URL=postgresql+psycopg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
   ```

   The `${{ ... }}` syntax is Railway's variable reference — it pulls
   values from the Postgres plugin automatically, so there's no secret
   to copy-paste and it rotates cleanly if the DB is replaced.

4. **Expose the service publicly.** In the service's *Settings → Networking*,
   click *Generate Domain*. Railway proxies `:443` to the container's
   `:8000`. No extra config needed — the Dockerfile already `EXPOSE`s 8000
   and `uvicorn` binds to `0.0.0.0`.

5. **Deploy.** Push to `main` (or whichever branch Railway is watching)
   and Railway builds the Dockerfile, runs the image, and serves the
   frontend + API from your generated domain. Tables are created on
   startup by `init_engine()`.

**Verifying:**
```bash
curl https://your-app.up.railway.app/healthz
curl https://your-app.up.railway.app/api/leaderboard
```

### Other platforms

The same pattern works anywhere that runs a Dockerfile. Set `DATABASE_URL`
to `postgresql+psycopg://user:pass@host:port/db` and expose port 8000.

- **Fly.io** — `fly launch`, then `fly postgres create && fly postgres attach`.
  Set `DATABASE_URL` to the `postgresql+psycopg://...` form in
  `fly.toml`.
- **Render** — New → Web Service → connect repo → Docker runtime. Add a
  Render Postgres addon, copy its External URL, and set `DATABASE_URL`
  with the scheme rewritten to `postgresql+psycopg://`.
- **Google Cloud Run + Cloud SQL** — build with `gcloud builds submit`,
  deploy with `gcloud run deploy`, and point `DATABASE_URL` at the Cloud
  SQL instance's private IP.

## Architecture notes

- **Single container, single port.** The Dockerfile builds the Vite
  frontend in a Node stage, then copies the `dist/` output into a Python
  stage where FastAPI mounts it at `/` with an SPA fallback. API routes
  are under `/api/*`; all other paths fall through to `index.html` so
  React Router's client-side routing keeps working.
- **Question generation** lives in `backend/app/questions.py`. Each
  question type has a factory that returns a dedup signature alongside
  the text/answer/explanation so a single quiz is guaranteed to contain
  10 distinct problems. Geometry pulls from a curated 120+ question pool
  that scales from K ("which shape has 3 sides?") to G5 hard (volumes,
  angle arithmetic, equilateral / isosceles / scalene).
- **Leaderboard** is written on quiz submission
  (`POST /api/quizzes/{id}/submit`) and read back via
  `GET /api/leaderboard?mathType=&difficulty=&grade=&limit=`.

See `openapi.yaml` for the full API contract.

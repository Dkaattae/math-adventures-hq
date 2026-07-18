# Deploying Math Adventures HQ (Railway + Supabase)

This guide deploys the app as a **single container** (the Dockerfile builds
the React frontend and bakes it into the FastAPI image, which serves both
the API and the SPA on one port) with a **Supabase Postgres** database.

- **Supabase** hosts the Postgres database.
- **Railway** builds and runs the container from this repo's `Dockerfile`.
- Database schema is managed by **Alembic**, which runs automatically on
  startup — no manual migration step required.

You'll need a [Supabase](https://supabase.com) account and a
[Railway](https://railway.app) account (both have free tiers).

---

## 1. Create the database on Supabase

1. In Supabase, **New project**. Pick a name, a strong **database
   password** (save it), and a region close to your Railway region.
2. Wait for the project to finish provisioning.
3. Open **Project Settings → Database → Connection string** and copy the
   **URI**. It looks like:

   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.<ref>.supabase.co:5432/postgres
   ```

   - Replace `[YOUR-PASSWORD]` with the password from step 1.
   - For a small app the direct connection (port `5432`) is fine. If you
     expect many concurrent connections, use Supabase's **connection
     pooler** URI (Transaction mode, port `6543`) instead.

   > You can paste this URL as-is. The app upgrades `postgresql://` to the
   > `postgresql+psycopg://` driver SQLAlchemy needs automatically
   > (see `app/db.py: normalize_database_url`).

Keep this connection string handy — it becomes `DATABASE_URL` on Railway.

---

## 2. Deploy the app on Railway

1. In Railway, **New Project → Deploy from GitHub repo** and pick this
   repository. Railway detects the `Dockerfile` at the repo root and uses
   it (no build config needed).
2. Open the service's **Variables** tab and add:

   | Variable       | Value                                             |
   |----------------|---------------------------------------------------|
   | `DATABASE_URL` | the Supabase connection string from step 1        |

   That's the only required variable. Optional ones:

   | Variable          | When to set it                                        |
   |-------------------|-------------------------------------------------------|
   | `SKIP_MIGRATIONS` | `1` to skip auto-migrations at startup (see §4)       |

3. **Networking:** open **Settings → Networking → Generate Domain**.
   Railway sets a `PORT` env var and the container binds to it
   automatically (the Dockerfile's `CMD` honors `${PORT:-8000}`).
4. Railway builds and deploys. On first boot the app runs
   `alembic upgrade head`, creating all tables in your Supabase database.
5. Visit the generated domain — you should see the MathQuest home screen,
   and `GET /healthz` should return `{"status":"ok"}`.

---

## 3. Verify

- **Health:** `https://<your-app>.up.railway.app/healthz` → `{"status":"ok"}`
- **App:** open the domain, create a player with a PIN, and play a quiz.
- **Database:** in Supabase, **Table Editor** should now show `users`,
  `quizzes`, `quiz_results`, `leaderboard`, and `alembic_version`.

---

## 4. Migrations

Schema changes are Alembic migrations in `backend/migrations/versions/`.
By default the app applies them on startup, so a normal deploy needs no
extra step.

If you'd rather run migrations as an explicit release step (recommended
once you have real data, to avoid multiple instances migrating at once):

1. Set `SKIP_MIGRATIONS=1` on the Railway service.
2. Add a **pre-deploy / release command** (Railway **Settings → Deploy →
   Custom Start Command** or a release phase) that runs, from the
   `backend/` working directory:

   ```bash
   alembic upgrade head
   ```

To create a new migration after changing the SQLAlchemy models
(`backend/app/db_models.py`), from `backend/` with `DATABASE_URL` set:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head   # apply locally
```

Review the generated file before committing — autogenerate is a starting
point, not gospel.

---

## 5. Local production-like run (optional)

To rehearse the container locally against Supabase (or any Postgres):

```bash
docker build -t math-adventures .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres" \
  math-adventures
# open http://localhost:8000
```

Or run everything locally with the bundled Postgres:

```bash
docker compose up -d --build   # app + local postgres, no Supabase needed
```

---

## Notes & gotchas

- **Driver:** the app needs the psycopg-v3 driver
  (`postgresql+psycopg://`). Pasting Supabase's `postgresql://` URL is
  fine — it's normalized at runtime.
- **Secrets:** never commit `DATABASE_URL`. It lives only in Railway's
  Variables. `.env*` files are git-ignored.
- **Password rotation:** if you rotate the Supabase DB password, update
  `DATABASE_URL` on Railway and redeploy.
- **PINs are hashed** (PBKDF2), forgotten PINs are recoverable via the
  one-time rescue code from signup, and 5 failed attempts lock an account
  for 15 minutes. Username creation itself is still unthrottled — see
  `PROJECT_PLAN.md` §2.
- **Cold starts / free tier:** both platforms may sleep idle services on
  free tiers; the first request after idle can be slow.

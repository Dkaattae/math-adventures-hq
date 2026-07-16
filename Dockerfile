# syntax=docker/dockerfile:1.6
#
# Single-image build: compile the Vite frontend, then bake it into a
# Python/FastAPI image that serves both the API and the static SPA on one
# port. One process, one container — easy to deploy.

# ---------- stage 1: build the frontend ----------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- stage 2: python runtime ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST=/app/frontend_dist

WORKDIR /app

# System deps for psycopg binary are pulled in by the wheel; no extra apt.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Backend source
COPY backend/ ./backend/

# Built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend_dist

WORKDIR /app/backend

EXPOSE 8000

# DATABASE_URL is injected by docker-compose / your deploy env.
# Bind to $PORT when the platform sets one (e.g. Railway), else 8000.
# Migrations run automatically at startup (see app.main lifespan).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

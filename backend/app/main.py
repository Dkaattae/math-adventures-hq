import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import init_engine, run_migrations
from .routers import leaderboard, quizzes, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bring the schema to head before serving. Set SKIP_MIGRATIONS=1 to
    # opt out (e.g. when a deploy runs `alembic upgrade head` separately).
    if os.environ.get("SKIP_MIGRATIONS") != "1":
        run_migrations()
    init_engine()
    yield


app = FastAPI(title="Math Adventures HQ API", version="0.1.0", lifespan=lifespan)

# CORS is only needed in dev when the frontend is served by Vite on another port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(quizzes.router)
app.include_router(leaderboard.router)


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}


# ---------- static frontend (production) ----------
#
# When the built frontend is present (e.g. inside the Docker image at
# /app/frontend_dist), mount it. In dev this directory doesn't exist, so we
# silently skip and let Vite serve the UI on :8080 with an /api proxy.

_STATIC_DIR = Path(os.environ.get("FRONTEND_DIST", "/app/frontend_dist"))

if _STATIC_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Let API routes 404 normally; only serve index.html for unknown paths.
        if full_path.startswith("api/") or full_path == "healthz":
            raise StarletteHTTPException(status_code=404)
        candidate = _STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")

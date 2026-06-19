from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import engine, Base
from app.core.limiter import limiter

# Import all models so SQLAlchemy knows about the tables before creating them
import app.models  # noqa: F401

# Import routers
from app.api import auth, workspaces, channels, messages, websocket, direct_messages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    # Create all database tables if they don't exist yet
    # In production you'd use Alembic migrations instead
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables ready")
    yield
    # Cleanup on shutdown
    await engine.dispose()
    print("✓ Database connections closed")


app = FastAPI(
    title=settings.APP_NAME,
    description="A Slack-like team communication platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Rate Limiting ───────────────────────────────────────────────────────────────
# Register the limiter so individual routes can use @limiter.limit(...).
# When someone exceeds a limit, _rate_limit_exceeded_handler returns a 429 error.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware ────────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Browsers block requests from one domain to another unless the server allows it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # open for development — restrict to your domain in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ─────────────────────────────────────────────────────────────────
# All REST endpoints are prefixed with /api
app.include_router(auth.router,        prefix="/api")
app.include_router(workspaces.router,  prefix="/api")
app.include_router(channels.router,    prefix="/api")
app.include_router(messages.router,    prefix="/api")
app.include_router(direct_messages.router, prefix="/api")

# WebSocket (no /api prefix — browsers use ws:// not http://)
app.include_router(websocket.router)


@app.get("/api/health")
async def health_check():
    """Simple endpoint to check if the server is running."""
    return {"status": "ok", "app": settings.APP_NAME}

# Serve uploaded files. This MUST be mounted before the catch-all "/" mount
# below — otherwise "/" would match first and uploads would 404.
import os
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Serve the frontend files directly from FastAPI
# This means everything runs on port 8000 — no nginx needed, no CORS issues
app.mount("/", StaticFiles(directory="/frontend", html=True), name="frontend")

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────
    APP_NAME: str = "TeamFlow"
    DEBUG: bool = False

    # Secret key signs JWT tokens — change this to a long random string in production
    SECRET_KEY: str = "change-me-to-a-long-random-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60       # access token lives 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7          # refresh token lives 7 days

    # ── File uploads ──────────────────────────────────────────────────────
    UPLOAD_DIR: str = "/uploads"                 # where files are saved on disk
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024      # 10 MB per file

    # ── Database ──────────────────────────────────────────────────────────
    # asyncpg is the async PostgreSQL driver; format: user:password@host/db
    DATABASE_URL: str = "postgresql+asyncpg://teamflow:teamflow@db:5432/teamflow"

    # ── Redis ─────────────────────────────────────────────────────────────
    # Redis broadcasts real-time messages across multiple server instances
    REDIS_URL: str = "redis://redis:6379"

    # ── CORS (Cross-Origin Resource Sharing) ─────────────────────────────
    # List of frontend addresses allowed to call our API
    ALLOWED_ORIGINS: List[str] = ["http://localhost", "http://localhost:8080"]

    class Config:
        env_file = ".env"   # reads secrets from a .env file at startup


settings = Settings()

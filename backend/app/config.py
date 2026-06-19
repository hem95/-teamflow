from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List

# Placeholder secrets that must NEVER be used in production
_WEAK_SECRETS = {
    "",
    "change-me-to-a-long-random-secret",
    "change-me-to-a-long-random-string-at-least-32-chars",
}


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────
    APP_NAME: str = "TeamFlow"
    DEBUG: bool = False

    # "development" (your laptop) or "production" (the cloud server).
    # Production turns on stricter safety checks (see the validator below).
    ENVIRONMENT: str = "development"

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

    @model_validator(mode="after")
    def _enforce_production_safety(self):
        """
        Refuse to start in production with insecure defaults.
        On your laptop ENVIRONMENT stays 'development', so none of this fires.
        """
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in _WEAK_SECRETS or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be a strong random value (32+ chars) in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if "teamflow:teamflow@" in self.DATABASE_URL:
                raise ValueError(
                    "The default database password is not allowed in production. "
                    "Set a strong POSTGRES_PASSWORD and update DATABASE_URL."
                )
        return self


settings = Settings()

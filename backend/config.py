"""
config.py — Application settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Reads settings from environment / .env file automatically.
    Supabase fields are optional since we can run with local SQLite.
    """
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # Local auth settings
    JWT_SECRET: str = "dynacalorie-local-dev-secret-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # Database
    DB_PATH: str = os.path.join(os.path.dirname(__file__), "dynacalorie.db")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global singleton - import 'settings' everywhere
settings = Settings()  # type: ignore[call-arg]

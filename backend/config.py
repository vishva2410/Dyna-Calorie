"""
config.py — Application settings loaded from environment variables.
Copy .env.example to .env and fill in your Supabase project credentials.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Reads required secrets from environment / .env file automatically.
    """
    SUPABASE_URL: str
    SUPABASE_KEY: str       # Use the anon/public key for client-side auth
    SUPABASE_SERVICE_KEY: str   # Use the service-role key for server-side admin ops

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global singleton - import 'settings' everywhere
settings = Settings()  # type: ignore[call-arg]

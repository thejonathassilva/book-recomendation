import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://bookstore:bookstore@localhost:5432/bookstore",
    )
    redis_url: str = os.environ.get("REDIS_URL", "")
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    admin_token: str = os.environ.get("ADMIN_TOKEN", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()

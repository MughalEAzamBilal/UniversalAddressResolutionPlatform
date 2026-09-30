import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Universal Address Resolution Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-32-chars-minimum-universal-address-2026"
    DATABASE_URL: str = "sqlite:///./data/address_platform.db"
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"
    DEFAULT_REDIRECT_SECONDS: int = 3
    ALLOWED_REDIRECT_DELAYS: List[int] = [0, 1, 2, 3, 5, 10, 15, 30]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    EDIT_SESSION_EXPIRE_MINUTES: int = 60  # 1 hour
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=(".env", "app/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

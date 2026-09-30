import os
from functools import lru_cache
from typing import List
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Automatically load app/.env or .env using absolute paths
for env_candidate in (
    os.path.join(BASE_DIR, "app", ".env"),
    os.path.join(BASE_DIR, ".env"),
    "app/.env",
    ".env",
):
    if os.path.exists(env_candidate):
        load_dotenv(env_candidate)
        break


class Settings:
    def __init__(self):
        self.BASE_DIR: str = BASE_DIR
        self.APP_NAME: str = os.getenv("APP_NAME", "Universal Address Resolution Platform")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-32-chars-minimum-universal-address-2026")
        
        raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./data/address_platform.db")
        if raw_db_url.startswith("sqlite:///./") or (raw_db_url.startswith("sqlite:///") and not raw_db_url.startswith("sqlite:////") and ":" not in raw_db_url[10:]):
            rel_file = raw_db_url.replace("sqlite:///", "").lstrip("./")
            abs_db_file = os.path.abspath(os.path.join(BASE_DIR, rel_file)).replace("\\", "/")
            self.DATABASE_URL = f"sqlite:///{abs_db_file}"
        else:
            self.DATABASE_URL = raw_db_url

        self.PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
        self.DEFAULT_REDIRECT_SECONDS: int = int(os.getenv("DEFAULT_REDIRECT_SECONDS", "3"))
        self.ALLOWED_REDIRECT_DELAYS: List[int] = [0, 1, 2, 3, 5, 10, 15, 30]
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
        self.EDIT_SESSION_EXPIRE_MINUTES: int = int(os.getenv("EDIT_SESSION_EXPIRE_MINUTES", "60"))
        self.MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.LOCKOUT_MINUTES: int = int(os.getenv("LOCKOUT_MINUTES", "15"))
        self.ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
        self.ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "fpfkA#S6KfJ1HVNoh#")


@lru_cache()
def get_settings() -> Settings:
    return Settings()

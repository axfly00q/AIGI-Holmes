"""
AIGI-Holmes backend — application settings loaded from environment / .env file.
"""

import os
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./aigi_holmes.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_ROLE_PASSWORD: str = "aigi"

    # Model
    MODEL_PATH: str = os.path.join(
        getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(__file__))),
        "finetuned_fake_real_resnet50.pth",
    )

    # Doubao AI
    DOUBAO_API_KEY: str = ""
    DOUBAO_MODEL: str = "doubao-pro-32k"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

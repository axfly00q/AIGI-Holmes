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

    # JWT — 生产环境必须在 .env 中设置非空的随机字符串
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_ROLE_PASSWORD: str = ""

    # CORS — 生产环境建议设置为实际域名，多个域名用英文逗号分隔
    # 例如: ALLOWED_ORIGINS=https://example.com,https://www.example.com
    # 留空或设为 * 表示允许所有来源（仅限本地开发）
    ALLOWED_ORIGINS: str = "*"

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

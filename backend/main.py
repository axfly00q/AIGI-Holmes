"""
AIGI-Holmes: FastAPI backend — main application entry point.

Replaces the legacy Flask server (server.py).
Run with:
    uvicorn backend.main:app --host 127.0.0.1 --port 7860 --reload
"""

import asyncio
import logging
import os
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request

from backend.cache import close_redis
from backend.config import get_settings
from backend.database import Base, engine
from backend.exceptions import register_exception_handlers
from backend.models.feedback import FeedbackRecord as _FeedbackRecord  # noqa: F401 — registers table
from backend.rate_limit import limiter
from backend.routers import auth, detect, report, admin, ws, feedback, history, search, text_detect, profile
from backend.clip_classify import _load_clip

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base directory
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# Lifespan — create DB tables on startup, close Redis on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _settings = get_settings()
    if not _settings.SECRET_KEY:
        logger.warning("[安全警告] SECRET_KEY 未配置，使用随机临时密钥（每次重启后所有 token 失效）")
    if not _settings.ADMIN_ROLE_PASSWORD:
        logger.warning("[安全警告] ADMIN_ROLE_PASSWORD 未配置，角色管理功能将不可用")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 在后台加载 CLIP 模型（不阻塞应用启动）
    def _preload_clip():
        try:
            logger.info("Preloading CLIP model in background...")
            _load_clip()
            logger.info("CLIP model preloaded successfully")
        except Exception as e:
            logger.warning("Failed to preload CLIP model: %s", str(e))
    
    # 使用线程池异步加载，不阻塞应用启动
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _preload_clip)

    # 在后台加载 RoBERTa 文本检测模型（不阻塞应用启动）
    def _preload_text_model():
        try:
            from backend.text_detect import _ensure_text_model
            logger.info("Preloading text detection model in background...")
            _ensure_text_model()
            logger.info("Text detection model preloaded successfully")
        except Exception as e:
            logger.warning("Failed to preload text detection model: %s", str(e))

    loop.run_in_executor(None, _preload_text_model)
    
    yield
    
    # Shutdown
    await close_redis()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title="AIGI-Holmes", version="2.0.0", lifespan=lifespan)

# 速率限制
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
_cors_origins_raw = get_settings().ALLOWED_ORIGINS
_cors_origins = (
    [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
    if _cors_origins_raw and _cors_origins_raw.strip() != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,   # JWT 使用 Authorization header，不需要 credentials 模式
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Routers
app.include_router(detect.router)
app.include_router(auth.router)
app.include_router(report.router)
app.include_router(admin.router)
app.include_router(ws.router)
app.include_router(feedback.router)
app.include_router(history.router)
app.include_router(search.router)
app.include_router(text_detect.router)
app.include_router(profile.router)

# Static files & templates
_static_dir = os.path.join(BASE_DIR, "static")
_template_dir = os.path.join(BASE_DIR, "templates")
_docs_dir = os.path.join(BASE_DIR, "static", "docs")

if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

import time as _time

templates = Jinja2Templates(directory=_template_dir) if os.path.isdir(_template_dir) else None

_CACHE_BUST = str(int(_time.time()))


@app.get("/")
async def landing(request: Request):
    if templates:
        return templates.TemplateResponse(request, "landing.html", {"cache_bust": _CACHE_BUST})
    return {"message": "AIGI-Holmes API is running. Visit /docs for API docs."}


@app.get("/app")
async def index(request: Request):
    if templates:
        return templates.TemplateResponse(request, "index.html", {"cache_bust": _CACHE_BUST})
    return {"message": "AIGI-Holmes API is running. Visit /docs for API docs."}

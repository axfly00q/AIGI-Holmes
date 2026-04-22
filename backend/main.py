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
from starlette.requests import Request

from backend.cache import close_redis
from backend.database import Base, engine
from backend.exceptions import register_exception_handlers
from backend.models.feedback import FeedbackRecord as _FeedbackRecord  # noqa: F401 — registers table
from backend.routers import auth, detect, report, admin, ws, feedback, history, search, text_detect
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
    
    yield
    
    # Shutdown
    await close_redis()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title="AIGI-Holmes", version="2.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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

# Static files & templates
_static_dir = os.path.join(BASE_DIR, "static")
_template_dir = os.path.join(BASE_DIR, "templates")

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

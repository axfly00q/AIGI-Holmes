"""
AIGI-Holmes: FastAPI backend — main application entry point.

Replaces the legacy Flask server (server.py).
Run with:
    uvicorn backend.main:app --host 127.0.0.1 --port 7860 --reload
"""

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
from backend.routers import auth, detect, report

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
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

# Static files & templates
_static_dir = os.path.join(BASE_DIR, "static")
_template_dir = os.path.join(BASE_DIR, "templates")

if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

templates = Jinja2Templates(directory=_template_dir) if os.path.isdir(_template_dir) else None


@app.get("/")
async def index(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return {"message": "AIGI-Holmes API is running. Visit /docs for API docs."}

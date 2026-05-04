"""
FastAPI 视图入口 — A-Share Market Dashboard
MANIFESTO II: 视图无状态 — 仅负责展示，不触及底层逻辑
MANIFESTO IV: 配置驱动 — 所有参数来自 config/
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config.settings import APP_TITLE, APP_VERSION, API_KEY
from data.fetcher import format_error_response
from logic.indicators import calc_change_pct

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"title": APP_TITLE, "version": APP_VERSION, "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": APP_VERSION}


@app.get("/api/key-status")
async def key_status():
    return {"configured": bool(API_KEY)}


@app.get("/api/demo/calc")
async def demo_calc(current: float = 100.0, previous: float = 95.0):
    result = calc_change_pct(current, previous)
    if result is None:
        raise HTTPException(status_code=400, detail="previous value cannot be zero")
    return {"current": current, "previous": previous, "change_pct": result}

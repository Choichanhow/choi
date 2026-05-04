"""
FastAPI 视图入口 — A-Share Market Dashboard
MANIFESTO II: 视图无状态 — 仅负责展示，不触及底层逻辑
MANIFESTO IV: 配置驱动 — 所有参数来自 config/
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import APP_TITLE, APP_VERSION, API_KEY
from view.routers.market import router as market_router

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_router)


@app.get("/")
async def root():
    return {"title": APP_TITLE, "version": APP_VERSION, "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": APP_VERSION}


@app.get("/api/key-status")
async def key_status():
    return {"configured": bool(API_KEY)}

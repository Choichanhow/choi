"""
统一配置中心 — A-Share Market Dashboard
MANIFESTO IV: 配置驱动 — 禁止硬编码任何参数
"""

import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "")

APP_TITLE = "A-Share Market Dashboard"
APP_VERSION = "0.2.0"
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_RELOAD = os.getenv("APP_RELOAD", "true").lower() == "true"

REFRESH_INTERVAL_SECONDS = int(os.getenv("REFRESH_INTERVAL", "30"))

CACHE_DIR = os.getenv("CACHE_DIR", "data/cache")
BREADTH_CACHE_TTL = int(os.getenv("BREADTH_CACHE_TTL", "300"))
INDEX_CACHE_TTL = int(os.getenv("INDEX_CACHE_TTL", "5"))

PYTDX_ENABLED = os.getenv("PYTDX_ENABLED", "false").lower() == "true"
PYTDX_MODE = os.getenv("PYTDX_MODE", "tcp")

INDEX_CODES = {
    "shanghai": "000001",
    "shenzhen": "399001",
    "chinext": "399006",
    "star_50": "000688",
    "star_composite": "000680",
    "csi_all": "000985",
}

INDEX_TDX_MAP = {
    "shanghai": (0, "000001"),
    "shenzhen": (0, "399001"),
    "chinext": (0, "399006"),
    "star_50": (0, "000688"),
    "star_composite": (0, "000680"),
    "csi_all": (0, "000985"),
}

PYTDX_BEST_SERVER = ("218.106.92.183", 7709)

DEFAULT_INDEX = "shanghai"

FALLBACK_VALUES = {
    "price": 0.0,
    "change_pct": 0.0,
    "volume": 0,
    "amount": 0.0,
}

ERROR_MESSAGE = "--"

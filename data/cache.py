"""
本地SQLite缓存 — A-Share Market Dashboard
MANIFESTO IV: 鲁棒性预设 — 缓存作为辅助层，不影响数据获取

缓存策略：
- 市场广度数据：缓存5分钟（可配置），减少60秒的等待
- 指数数据：缓存5秒（可配置）
"""

import sqlite3
import time
import json
import os
from typing import Optional

from config.settings import CACHE_DIR, BREADTH_CACHE_TTL, INDEX_CACHE_TTL

CACHE_DB = os.path.join(CACHE_DIR, "market_cache.db")


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _get_conn():
    _ensure_cache_dir()
    conn = sqlite3.connect(CACHE_DB, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_cache (
            key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def get_cache(key: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT data, timestamp FROM market_cache WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            data, timestamp = row
            return json.loads(data)
        return None
    finally:
        conn.close()


def set_cache(key: str, data: dict, ttl: int = BREADTH_CACHE_TTL):
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO market_cache (key, data, timestamp)
            VALUES (?, ?, ?)
        """, (key, json.dumps(data), time.time() + ttl))
        conn.commit()
    finally:
        conn.close()


def get_breadth_cache() -> Optional[dict]:
    return get_cache("market_breadth")


def set_breadth_cache(data: dict):
    set_cache("market_breadth", data, BREADTH_CACHE_TTL)


def get_indices_cache() -> Optional[dict]:
    return get_cache("indices")


def set_indices_cache(data: dict):
    set_cache("indices", data, INDEX_CACHE_TTL)


def clear_expired_cache():
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM market_cache WHERE timestamp < ?",
            (time.time(),)
        )
        conn.commit()
    finally:
        conn.close()

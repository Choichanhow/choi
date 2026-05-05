"""
本地SQLite缓存模块 — A-Share Market Dashboard
MANIFESTO IV: 鲁棒性预设 — 缓存作为辅助层，不影响数据获取

缓存策略：
- 市场广度数据：缓存5分钟（可配置）
- 指数数据：缓存5秒（可配置）
- 每日数据：按交易日存储，永不过期（由local_storage管理）

修复内容：
1. 缓存数据有效性验证（日期匹配检查）
2. 缓存清理策略（定期清理过期数据）
3. 缓存与实时数据隔离
"""

import sqlite3
import time
import json
import os
import datetime
from typing import Optional, Dict, Any

from config.settings import CACHE_DIR, BREADTH_CACHE_TTL, INDEX_CACHE_TTL

CACHE_DB = os.path.join(CACHE_DIR, "market_cache.db")


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _get_conn():
    _ensure_cache_dir()
    conn = sqlite3.connect(CACHE_DB, check_same_thread=False)
    _init_tables(conn)
    return conn


def _init_tables(conn):
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_cache (
            key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            timestamp REAL NOT NULL,
            trading_date TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    
    conn.commit()


def get_cache(key: str) -> Optional[dict]:
    """获取缓存数据，自动检查有效性"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT data, timestamp, trading_date FROM market_cache WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            data_str, timestamp, trading_date = row
            
            if timestamp < time.time():
                delete_cache(key)
                return None
            
            try:
                data = json.loads(data_str)
                
                if trading_date:
                    data["_cached_trading_date"] = trading_date
                data["_cached_at"] = timestamp
                
                return data
            except json.JSONDecodeError:
                delete_cache(key)
                return None
        return None
    finally:
        conn.close()


def set_cache(key: str, data: dict, ttl: int = BREADTH_CACHE_TTL, trading_date: Optional[str] = None):
    """设置缓存，支持交易日期标记"""
    conn = _get_conn()
    try:
        expire_time = time.time() + ttl
        
        cleaned_data = {k: v for k, v in data.items() if not k.startswith("_")}
        
        conn.execute("""
            INSERT OR REPLACE INTO market_cache 
            (key, data, timestamp, trading_date)
            VALUES (?, ?, ?, ?)
        """, (key, json.dumps(cleaned_data), expire_time, trading_date))
        conn.commit()
    finally:
        conn.close()


def delete_cache(key: str):
    """删除指定缓存"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM market_cache WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()


def get_breadth_cache() -> Optional[dict]:
    return get_cache("market_breadth")


def set_breadth_cache(data: dict):
    trading_date = data.get("trading_date") or data.get("date")
    set_cache("market_breadth", data, BREADTH_CACHE_TTL, trading_date)


def get_indices_cache() -> Optional[dict]:
    return get_cache("indices")


def set_indices_cache(data: dict):
    set_cache("indices", data, INDEX_CACHE_TTL)


def clear_expired_cache():
    """清理所有过期缓存"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM market_cache WHERE timestamp < ?", (time.time(),))
        conn.commit()
    finally:
        conn.close()


def clear_all_cache():
    """清理所有缓存（用于测试或强制刷新）"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM market_cache")
        conn.commit()
    finally:
        conn.close()


def is_cache_valid(key: str, expected_trading_date: Optional[str] = None) -> bool:
    """
    检查缓存是否有效
    
    Args:
        key: 缓存键
        expected_trading_date: 期望的交易日期（可选）
    
    Returns:
        True if cache is valid and not expired
    """
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT timestamp, trading_date FROM market_cache WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if not row:
            return False
        
        timestamp, trading_date = row
        
        if timestamp < time.time():
            return False
        
        if expected_trading_date and trading_date != expected_trading_date:
            return False
        
        return True
    finally:
        conn.close()


def validate_cache_data(data: dict, expected_trading_date: Optional[str] = None) -> bool:
    """
    验证缓存数据的有效性
    
    Args:
        data: 缓存数据
        expected_trading_date: 期望的交易日期
    
    Returns:
        True if data is valid
    """
    if not isinstance(data, dict):
        return False
    
    if data.get("error"):
        return False
    
    cached_date = data.get("_cached_trading_date")
    if expected_trading_date and cached_date and cached_date != expected_trading_date:
        return False
    
    if "_cached_at" in data:
        if data["_cached_at"] < time.time():
            return False
    
    return True


def get_cache_info() -> dict:
    """获取缓存统计信息"""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM market_cache")
        count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM market_cache WHERE timestamp > ?", (time.time(),))
        valid_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM market_cache")
        min_ts, max_ts = cursor.fetchone()
        
        oldest = datetime.datetime.fromtimestamp(min_ts).strftime("%Y-%m-%d %H:%M:%S") if min_ts else None
        newest = datetime.datetime.fromtimestamp(max_ts).strftime("%Y-%m-%d %H:%M:%S") if max_ts else None
        
        return {
            "total_entries": count,
            "valid_entries": valid_count,
            "expired_entries": count - valid_count,
            "oldest_entry": oldest,
            "newest_entry": newest,
        }
    finally:
        conn.close()


def update_cache_metadata(key: str, value: str):
    """更新缓存元数据"""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO cache_metadata (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, time.time()))
        conn.commit()
    finally:
        conn.close()


def get_cache_metadata(key: str, default: str = "") -> str:
    """获取缓存元数据"""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT value FROM cache_metadata WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default
    finally:
        conn.close()


def periodic_cache_cleanup(max_age_hours: int = 24):
    """
    定期清理缓存
    
    Args:
        max_age_hours: 最大保留时间（小时）
    """
    conn = _get_conn()
    try:
        cutoff_time = time.time() - (max_age_hours * 3600)
        conn.execute("DELETE FROM market_cache WHERE timestamp < ?", (cutoff_time,))
        conn.commit()
    finally:
        conn.close()

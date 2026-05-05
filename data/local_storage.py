"""
本地数据库存储模块 — A-Share Market Dashboard
MANIFESTO IV: 鲁棒性预设 — 数据本地存储，降低网络依赖

功能：
1. 将市场数据按日期结构存储到SQLite
2. 实现数据访问优先级机制（本地优先）
3. 确保展示的是最新已收盘交易日的收盘价
"""

import sqlite3
import json
import os
import datetime
from typing import Optional, Dict, Any

from data.trading_dates import get_last_trading_date

DB_DIR = "data/db"
DB_PATH = os.path.join(DB_DIR, "market_data.db")


def _convert_to_native(obj):
    """将numpy/pandas类型转换为Python原生类型"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_native(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


def _ensure_db_dir():
    os.makedirs(DB_DIR, exist_ok=True)


def _get_conn():
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _init_tables(conn)
    return conn


def _init_tables(conn):
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_index_data (
            trading_date TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_market_breadth (
            trading_date TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_sectors (
            trading_date TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    conn.commit()


def save_daily_index_data(trading_date: datetime.date, data: dict):
    """保存每日指数数据"""
    conn = _get_conn()
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        now = datetime.datetime.now().timestamp()
        native_data = _convert_to_native(data)

        conn.execute("""
            INSERT OR REPLACE INTO daily_index_data
            (trading_date, data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (date_str, json.dumps(native_data), now, now))

        conn.commit()
    finally:
        conn.close()


def get_daily_index_data(trading_date: datetime.date) -> Optional[dict]:
    """获取指定交易日的指数数据"""
    conn = _get_conn()
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        cursor = conn.execute(
            "SELECT data FROM daily_index_data WHERE trading_date = ?",
            (date_str,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()


def save_daily_market_breadth(trading_date: datetime.date, data: dict):
    """保存每日市场广度数据"""
    conn = _get_conn()
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        now = datetime.datetime.now().timestamp()
        native_data = _convert_to_native(data)

        conn.execute("""
            INSERT OR REPLACE INTO daily_market_breadth
            (trading_date, data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (date_str, json.dumps(native_data), now, now))

        conn.commit()
    finally:
        conn.close()


def get_daily_market_breadth(trading_date: datetime.date) -> Optional[dict]:
    """获取指定交易日的市场广度数据"""
    conn = _get_conn()
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        cursor = conn.execute(
            "SELECT data FROM daily_market_breadth WHERE trading_date = ?",
            (date_str,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()


def save_daily_sectors(trading_date: datetime.date, data: list):
    """保存每日板块数据"""
    conn = _get_conn()
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        now = datetime.datetime.now().timestamp()
        native_data = _convert_to_native(data)

        conn.execute("""
            INSERT OR REPLACE INTO daily_sectors
            (trading_date, data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (date_str, json.dumps(native_data), now, now))

        conn.commit()
    finally:
        conn.close()


def get_daily_sectors(trading_date: datetime.date) -> Optional[list]:
    """获取指定交易日的板块数据"""
    conn = _get_conn()
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        cursor = conn.execute(
            "SELECT data FROM daily_sectors WHERE trading_date = ?",
            (date_str,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()


def get_latest_available_date(table_name: str) -> Optional[datetime.date]:
    """获取指定表中最新的交易日"""
    conn = _get_conn()
    try:
        cursor = conn.execute(f"SELECT MAX(trading_date) FROM {table_name}")
        row = cursor.fetchone()
        if row and row[0]:
            return datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
        return None
    finally:
        conn.close()


def get_index_data_with_fallback(trading_date: Optional[datetime.date] = None) -> Optional[dict]:
    """
    获取指数数据，优先从本地获取
    
    优先级：
    1. 指定交易日的数据（如果存在）
    2. 最新可用数据（回退策略）
    """
    if trading_date is None:
        trading_date = get_last_trading_date()
    
    if trading_date is None:
        return None
    
    data = get_daily_index_data(trading_date)
    if data:
        return data
    
    latest_date = get_latest_available_date("daily_index_data")
    if latest_date:
        return get_daily_index_data(latest_date)
    
    return None


def get_breadth_data_with_fallback(trading_date: Optional[datetime.date] = None) -> Optional[dict]:
    """
    获取市场广度数据，优先从本地获取
    """
    if trading_date is None:
        trading_date = get_last_trading_date()
    
    if trading_date is None:
        return None
    
    data = get_daily_market_breadth(trading_date)
    if data:
        return data
    
    latest_date = get_latest_available_date("daily_market_breadth")
    if latest_date:
        return get_daily_market_breadth(latest_date)
    
    return None


def get_sectors_data_with_fallback(trading_date: Optional[datetime.date] = None) -> Optional[list]:
    """
    获取板块数据，优先从本地获取
    """
    if trading_date is None:
        trading_date = get_last_trading_date()
    
    if trading_date is None:
        return None
    
    data = get_daily_sectors(trading_date)
    if data:
        return data
    
    latest_date = get_latest_available_date("daily_sectors")
    if latest_date:
        return get_daily_sectors(latest_date)
    
    return None


def is_data_fresh(trading_date: datetime.date, max_hours: int = 24) -> bool:
    """检查指定交易日的数据是否新鲜"""
    conn = _get_conn()
    try:
        date_str = trading_date.strftime("%Y-%m-%d")
        cursor = conn.execute(
            "SELECT updated_at FROM daily_index_data WHERE trading_date = ?",
            (date_str,)
        )
        row = cursor.fetchone()
        if row:
            updated_at = row[0]
            now = datetime.datetime.now().timestamp()
            hours_since_update = (now - updated_at) / 3600
            return hours_since_update <= max_hours
        return False
    finally:
        conn.close()


def save_system_config(key: str, value: str):
    """保存系统配置"""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO system_config (key, value)
            VALUES (?, ?)
        """, (key, value))
        conn.commit()
    finally:
        conn.close()


def get_system_config(key: str, default: str = "") -> str:
    """获取系统配置"""
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT value FROM system_config WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else default
    finally:
        conn.close()


def cleanup_old_data(days_to_keep: int = 90):
    """清理指定天数之前的历史数据"""
    conn = _get_conn()
    try:
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        conn.execute("DELETE FROM daily_index_data WHERE trading_date < ?", (cutoff_str,))
        conn.execute("DELETE FROM daily_market_breadth WHERE trading_date < ?", (cutoff_str,))
        conn.execute("DELETE FROM daily_sectors WHERE trading_date < ?", (cutoff_str,))
        
        conn.commit()
    finally:
        conn.close()


def get_data_summary() -> dict:
    """获取数据库数据摘要"""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM daily_index_data")
        index_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM daily_market_breadth")
        breadth_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM daily_sectors")
        sectors_count = cursor.fetchone()[0]
        
        latest_index = get_latest_available_date("daily_index_data")
        latest_breadth = get_latest_available_date("daily_market_breadth")
        latest_sectors = get_latest_available_date("daily_sectors")
        
        return {
            "index_records": index_count,
            "breadth_records": breadth_count,
            "sectors_records": sectors_count,
            "latest_index_date": latest_index.strftime("%Y-%m-%d") if latest_index else None,
            "latest_breadth_date": latest_breadth.strftime("%Y-%m-%d") if latest_breadth else None,
            "latest_sectors_date": latest_sectors.strftime("%Y-%m-%d") if latest_sectors else None,
        }
    finally:
        conn.close()

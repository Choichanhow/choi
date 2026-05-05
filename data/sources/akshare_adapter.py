"""
AKShare 数据源适配器 — A-Share Market Dashboard
MANIFESTO II: 数据原子化 — 只负责"拿"，不负责"算"
MANIFESTO IV: 鲁棒性预设 — 所有接口必须有降级处理

优化点：
1. 批量获取: 一次 HTTP 请求拉取全量指数，本地筛选，节省 2/3 请求
2. 内存缓存: 板块数据 30s TTL，指数数据 5s TTL
3. 并发安全: 使用 asyncio.Lock 防止竞态条件
4. 超时保护: 市场广度获取设置 120s 超时，防止挂起
5. SQLite本地缓存: 市场广度缓存5分钟，减少等待
"""

import asyncio
import time
from typing import Optional

import io
import sys

import akshare as ak
import pandas as pd

from data.cache import get_breadth_cache, set_breadth_cache
from data.fetcher import safe_fetch, format_error_response
from config.settings import (
    INDEX_CODES, INDEX_TDX_MAP, FALLBACK_VALUES, ERROR_MESSAGE
)


def _silent_exec(func, *args, **kwargs):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        return func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

BREADTH_TIMEOUT = 120.0


class AKShareAdapter:
    name = "akshare"
    supported_index_codes = INDEX_CODES

    _all_indices_df: Optional[pd.DataFrame] = None
    _indices_cache_time: float = 0
    INDICES_CACHE_TTL: float = 5.0

    _sector_cache: Optional[list] = None
    _sector_cache_time: float = 0
    SECTOR_CACHE_TTL: float = 30.0

    _indices_lock: asyncio.Lock = None
    _sector_lock: asyncio.Lock = None

    def __init__(self):
        self._indices_lock = asyncio.Lock()
        self._sector_lock = asyncio.Lock()

    async def fetch_index_realtime(self, index_code: str) -> dict:
        df = await self._fetch_all_indices_cached()
        if df is None or df.empty:
            return format_error_response("AKSHARE_NO_DATA")

        code = INDEX_CODES.get(index_code, index_code)
        row = df[df["代码"] == code]
        if row.empty:
            return format_error_response(f"AKSHARE_INDEX_NOT_FOUND: {index_code}")

        row = row.iloc[0]
        return {
            "source": self.name,
            "index_code": index_code,
            "code": safe_fetch(row, "代码", ERROR_MESSAGE),
            "name": safe_fetch(row, "名称", "未知"),
            "price": safe_fetch(row, "最新价", FALLBACK_VALUES["price"]),
            "change_pct": safe_fetch(row, "涨跌幅", FALLBACK_VALUES["change_pct"]),
            "change_amount": safe_fetch(row, "涨跌额", 0.0),
            "volume": safe_fetch(row, "成交量", FALLBACK_VALUES["volume"]),
            "amount": safe_fetch(row, "成交额", FALLBACK_VALUES["amount"]),
            "open": safe_fetch(row, "今开", 0.0),
            "high": safe_fetch(row, "最高", 0.0),
            "low": safe_fetch(row, "最低", 0.0),
            "prev_close": safe_fetch(row, "昨收", 0.0),
        }

    async def _fetch_all_indices_cached(self) -> Optional[pd.DataFrame]:
        now = time.time()
        async with self._indices_lock:
            if (
                self._all_indices_df is not None
                and (now - self._indices_cache_time) < self.INDICES_CACHE_TTL
            ):
                return self._all_indices_df

            try:
                df = await asyncio.to_thread(
                    ak.stock_zh_index_spot_em, symbol="沪深重要指数"
                )
                if df is not None and not df.empty:
                    self._all_indices_df = df
                    self._indices_cache_time = now
                return df
            except Exception as e:
                import logging
                logging.warning(f"AKShare指数获取失败: {type(e).__name__}, {str(e)}")
                return self._all_indices_df

    async def fetch_all_indices(self) -> list[dict]:
        df = await self._fetch_all_indices_cached()
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.iterrows():
            result.append({
                "source": self.name,
                "code": safe_fetch(row, "代码", ERROR_MESSAGE),
                "name": safe_fetch(row, "名称", ERROR_MESSAGE),
                "price": safe_fetch(row, "最新价", FALLBACK_VALUES["price"]),
                "change_pct": safe_fetch(row, "涨跌幅", FALLBACK_VALUES["change_pct"]),
                "volume": safe_fetch(row, "成交量", FALLBACK_VALUES["volume"]),
                "amount": safe_fetch(row, "成交额", FALLBACK_VALUES["amount"]),
            })
        return result

    async def fetch_sector_list(self, use_cache: bool = True) -> list[dict]:
        now = time.time()
        async with self._sector_lock:
            if use_cache and self._sector_cache and (now - self._sector_cache_time) < self.SECTOR_CACHE_TTL:
                return self._sector_cache

            try:
                df = await asyncio.to_thread(ak.stock_board_industry_name_em)
                if df is None or df.empty:
                    return []
                result = []
                for _, row in df.iterrows():
                    result.append({
                        "source": self.name,
                        "rank": safe_fetch(row, "排名", 0),
                        "sector_name": safe_fetch(row, "板块名称", ERROR_MESSAGE),
                        "sector_code": safe_fetch(row, "板块代码", ERROR_MESSAGE),
                        "price": safe_fetch(row, "最新价", FALLBACK_VALUES["price"]),
                        "change_pct": safe_fetch(row, "涨跌幅", FALLBACK_VALUES["change_pct"]),
                        "change_amount": safe_fetch(row, "涨跌额", 0.0),
                        "up_count": safe_fetch(row, "上涨家数", 0),
                        "down_count": safe_fetch(row, "下跌家数", 0),
                        "lead_stock": safe_fetch(row, "领涨股票", ERROR_MESSAGE),
                        "lead_change_pct": safe_fetch(row, "领涨股票-涨跌幅", FALLBACK_VALUES["change_pct"]),
                    })

                self._sector_cache = result
                self._sector_cache_time = now
                return result
            except Exception as e:
                import logging
                logging.warning(f"AKShare板块获取失败: {type(e).__name__}, {str(e)}")
                return [{"error": True, "reason": f"AKSHARE_SECTOR_ERROR: {type(e).__name__}"}]

    async def fetch_stock_realtime(self, stock_code: str) -> dict:
        try:
            df = await asyncio.to_thread(
                ak.stock_zh_a_spot_em, symbol=stock_code
            )
            if df is None or df.empty:
                return format_error_response("AKSHARE_STOCK_NO_DATA")
            row = df.iloc[0]
            return {
                "source": self.name,
                "code": stock_code,
                "name": safe_fetch(row, "名称", ERROR_MESSAGE),
                "price": safe_fetch(row, "最新价", FALLBACK_VALUES["price"]),
                "change_pct": safe_fetch(row, "涨跌幅", FALLBACK_VALUES["change_pct"]),
                "volume": safe_fetch(row, "成交量", FALLBACK_VALUES["volume"]),
                "amount": safe_fetch(row, "成交额", FALLBACK_VALUES["amount"]),
            }
        except Exception as e:
            return format_error_response(f"AKSHARE_STOCK_ERROR: {type(e).__name__}")

    async def fetch_zt_pool(self) -> list[dict]:
        try:
            df = await asyncio.to_thread(ak.stock_zt_pool_em)
            if df is None or df.empty:
                return []
            result = []
            for _, row in df.head(20).iterrows():
                result.append({
                    "source": self.name,
                    "code": safe_fetch(row, "代码", ERROR_MESSAGE),
                    "name": safe_fetch(row, "名称", ERROR_MESSAGE),
                    "close": safe_fetch(row, "最新价", 0.0),
                    "change_pct": safe_fetch(row, "涨停统计", 0.0),
                    "turnover_rate": safe_fetch(row, "换手率", 0.0),
                })
            return result
        except Exception as e:
            return [{"error": True, "reason": f"AKSHARE_ZT_ERROR: {type(e).__name__}"}]

    async def fetch_market_breadth(self) -> dict:
        cached = get_breadth_cache()
        if cached:
            return cached

        try:
            df = await asyncio.wait_for(
                asyncio.to_thread(_silent_exec, ak.stock_zh_a_spot_em),
                timeout=BREADTH_TIMEOUT
            )
            if df is None or df.empty:
                return {"error": True, "reason": "NO_DATA"}

            up_count = len(df[df["涨跌幅"] > 0])
            down_count = len(df[df["涨跌幅"] < 0])
            flat_count = len(df[df["涨跌幅"] == 0])
            total = len(df)

            result = {
                "source": self.name,
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "total": total,
                "ratio": round((up_count - down_count) / total * 100, 2) if total > 0 else 0,
            }

            set_breadth_cache(result)
            return result
        except asyncio.TimeoutError:
            import logging
            logging.warning(f"AKShare市场广度获取超时: {BREADTH_TIMEOUT}秒")
            return {"error": True, "reason": "BREADTH_TIMEOUT"}
        except Exception as e:
            import logging
            logging.warning(f"AKShare市场广度获取失败: {type(e).__name__}, {str(e)}")
            return {"error": True, "reason": f"AKSHARE_BREADTH_ERROR: {type(e).__name__}"}

    async def fetch_all_dashboard_data(self) -> dict:
        index_tasks = [
            self.fetch_index_realtime("shanghai"),
            self.fetch_index_realtime("shenzhen"),
            self.fetch_index_realtime("chinext"),
        ]
        sh, sz, cy = await asyncio.gather(*index_tasks, return_exceptions=True)

        breadth = await self.fetch_market_breadth()
        sectors = await self.fetch_sector_list()

        top_sectors = sorted(
            [s for s in sectors if "error" not in s],
            key=lambda x: x.get("change_pct", 0) or 0,
            reverse=True
        )[:10]

        return {
            "indices": {
                "shanghai": sh if not isinstance(sh, Exception) else format_error_response("SH_ERROR"),
                "shenzhen": sz if not isinstance(sz, Exception) else format_error_response("SZ_ERROR"),
                "chinext": cy if not isinstance(cy, Exception) else format_error_response("CY_ERROR"),
            },
            "market_breadth": breadth,
            "top_sectors": top_sectors,
        }

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(
                ak.stock_zh_index_spot_em, symbol="沪深重要指数"
            )
            return True
        except Exception:
            return False

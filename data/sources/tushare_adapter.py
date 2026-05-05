"""
Tushare 数据源适配器 — A-Share Market Dashboard
MANIFESTO II: 数据原子化 — 只负责"拿"，不负责"算"
MANIFESTO IV: 鲁棒性预设 — 所有接口必须有降级处理

使用条件：
- 需要 Tushare Token
- 需要网络连通
- 适合需要标准化数据或历史数据的场景
"""

import asyncio
from typing import Optional

from data.sources.config import TUSHARE_TOKEN
from data.fetcher import safe_fetch, format_error_response
from config.settings import (
    INDEX_CODES, FALLBACK_VALUES, ERROR_MESSAGE
)


class TushareAdapter:
    name = "tushare"
    supported_index_codes = INDEX_CODES

    _ts = None

    def __init__(self):
        self._ts = None

    def _get_client(self):
        if self._ts is None and TUSHARE_TOKEN:
            try:
                import tushare as ts
                self._ts = ts.pro(TUSHARE_TOKEN)
            except Exception:
                pass
        return self._ts

    async def fetch_index_realtime(self, index_code: str) -> dict:
        try:
            ts = self._get_client()
            if not ts:
                return format_error_response("TUSHARE_NOT_CONFIGURED")

            code = INDEX_CODES.get(index_code, index_code)

            df = await asyncio.to_thread(
                ts.index_daily, ts_code=code
            )

            if df is None or df.empty:
                return format_error_response("TUSHARE_NO_DATA")

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            price = safe_fetch(latest, "close", 0)
            prev_close = safe_fetch(prev, "close", 0)
            change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0

            return {
                "source": self.name,
                "index_code": index_code,
                "code": code,
                "name": index_code.replace("_", " ").title(),
                "price": price,
                "change_pct": change_pct,
                "change_amount": round(price - prev_close, 2) if price and prev_close else 0,
                "prev_close": prev_close,
            }
        except Exception as e:
            return format_error_response(f"TUSHARE_ERROR: {type(e).__name__}")

    async def fetch_market_breadth(self) -> dict:
        try:
            ts = self._get_client()
            if not ts:
                return {"error": True, "reason": "TUSHARE_NOT_CONFIGURED"}

            df = await asyncio.to_thread(
                ts.stock_basic, exchange="", list_status="L",
                fields="symbol,name"
            )

            if df is None or df.empty:
                return {"error": True, "reason": "TUSHARE_NO_DATA"}

            total = len(df)

            up_count = down_count = 0
            for _, row in df.iterrows():
                try:
                    price_data = await asyncio.to_thread(
                        ts.daily, ts_code=row["symbol"], start_date="", end_date=""
                    )
                    if price_data is not None and not price_data.empty:
                        latest = price_data.iloc[-1]
                        change = safe_fetch(latest, "pct_chg", 0) or 0
                        if change > 0:
                            up_count += 1
                        elif change < 0:
                            down_count += 1
                except Exception:
                    continue

            return {
                "source": self.name,
                "up_count": up_count,
                "down_count": down_count,
                "total": total,
                "ratio": round((up_count - down_count) / total * 100, 2) if total > 0 else 0,
            }
        except Exception as e:
            return {"error": True, "reason": f"TUSHARE_BREADTH_ERROR: {type(e).__name__}"}

    async def fetch_sector_list(self) -> list[dict]:
        try:
            ts = self._get_client()
            if not ts:
                return [{"error": True, "reason": "TUSHARE_NOT_CONFIGURED"}]

            df = await asyncio.to_thread(ts.index_classify)

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append({
                    "source": self.name,
                    "sector_name": safe_fetch(row, "name", ERROR_MESSAGE),
                    "sector_code": safe_fetch(row, "code", ERROR_MESSAGE),
                    "change_pct": 0,
                })
            return result
        except Exception as e:
            return [{"error": True, "reason": f"TUSHARE_SECTOR_ERROR: {type(e).__name__}"}]

    async def health_check(self) -> bool:
        return self._get_client() is not None

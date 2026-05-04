"""
Mootdx 数据源适配器 — A-Share Market Dashboard
MANIFESTO II: 数据原子化 — 只负责"拿"，不负责"算"
MANIFESTO IV: 鲁棒性预设 — 所有接口必须有降级处理

注意: Mootdx 0.11.x API 较简单，主要用于读取本地缓存/离线数据
      实时行情优先使用 AKShare
"""

import asyncio
from typing import Optional

from data.fetcher import safe_fetch, format_error_response
from config.settings import INDEX_CODES, FALLBACK_VALUES, ERROR_MESSAGE


class MootdxAdapter:
    name = "mootdx"
    supported_index_codes = INDEX_CODES

    async def fetch_index_realtime(self, index_code: str) -> dict:
        try:
            from mootdx.reader import Reader
            reader = Reader()
            code = self._to_standard_code(index_code)
            df = await asyncio.to_thread(reader.factory, index=code)
            if df is None or df.empty:
                return format_error_response("MOOTDX_NO_DATA")
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            close = safe_fetch(latest, "close", 0)
            prev_close = safe_fetch(prev, "close", 1)
            change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0
            return {
                "source": self.name,
                "index_code": index_code,
                "name": safe_fetch(latest, "name", ERROR_MESSAGE),
                "price": close,
                "change_pct": change_pct,
                "open": safe_fetch(latest, "open", 0.0),
                "high": safe_fetch(latest, "high", 0.0),
                "low": safe_fetch(latest, "low", 0.0),
                "volume": safe_fetch(latest, "vol", FALLBACK_VALUES["volume"]),
                "amount": safe_fetch(latest, "amount", FALLBACK_VALUES["amount"]),
                "prev_close": prev_close,
            }
        except Exception as e:
            return format_error_response(f"MOOTDX_ERROR: {type(e).__name__}")

    async def fetch_stock_realtime(self, stock_code: str) -> dict:
        try:
            from mootdx.reader import Reader
            reader = Reader()
            df = await asyncio.to_thread(reader.factory, symbol=stock_code)
            if df is None or df.empty:
                return format_error_response("MOOTDX_STOCK_NO_DATA")
            latest = df.iloc[-1]
            return {
                "source": self.name,
                "code": stock_code,
                "name": safe_fetch(latest, "name", ERROR_MESSAGE),
                "price": safe_fetch(latest, "close", FALLBACK_VALUES["price"]),
                "change_pct": safe_fetch(latest, "pct_chg", FALLBACK_VALUES["change_pct"]),
                "volume": safe_fetch(latest, "vol", FALLBACK_VALUES["volume"]),
                "amount": safe_fetch(latest, "amount", FALLBACK_VALUES["amount"]),
            }
        except Exception as e:
            return format_error_response(f"MOOTDX_STOCK_ERROR: {type(e).__name__}")

    async def fetch_index_list(self) -> list[dict]:
        try:
            from mootdx.reader import Reader
            reader = Reader()
            codes = ["000001", "399001", "399006", "000688"]
            result = []
            for code in codes:
                df = await asyncio.to_thread(reader.factory, index=code)
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    close = safe_fetch(latest, "close", 0)
                    prev_close = safe_fetch(prev, "close", 1)
                    change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0
                    result.append({
                        "source": self.name,
                        "code": code,
                        "name": safe_fetch(latest, "name", ERROR_MESSAGE),
                        "close": close,
                        "change_pct": change_pct,
                        "volume": safe_fetch(latest, "vol", 0),
                        "amount": safe_fetch(latest, "amount", 0.0),
                    })
            return result
        except Exception as e:
            return [{"error": True, "reason": f"MOOTDX_INDEX_LIST_ERROR: {type(e).__name__}"}]

    async def health_check(self) -> bool:
        try:
            from mootdx.reader import Reader
            reader = Reader()
            await asyncio.to_thread(reader.factory, index="000001")
            return True
        except Exception:
            return False

    def _to_standard_code(self, index_code: str) -> str:
        mapping = {
            "shanghai": "000001",
            "shenzhen": "399001",
            "chinext": "399006",
            "star_50": "000688",
        }
        return mapping.get(index_code, "000001")

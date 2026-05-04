"""
Pytdx 数据源适配器 — A-Share Market Dashboard
MANIFESTO II: 数据原子化 — 只负责"拿"，不负责"算"
MANIFESTO IV: 鲁棒性预设 — 所有接口必须有降级处理

依赖 pytdx，通过 UDP 直连通达信行情服务器（端口 7709）
需要网络能访问 TDX 服务器（部分网络环境可能不可用）
"""

import asyncio
from typing import Optional

from data.fetcher import safe_fetch, format_error_response
from config.settings import INDEX_CODES, FALLBACK_VALUES, ERROR_MESSAGE


INDEX_TDX_MAP = {
    "shanghai": ("0", "000001"),
    "shenzhen": ("0", "399001"),
    "chinext": ("0", "399006"),
    "star_50": ("0", "000688"),
}


class PytdxAdapter:
    name = "pytdx"
    supported_index_codes = INDEX_CODES

    def _get_quote(self, market: str, code: str) -> dict:
        try:
            from pytdx.hq import TdxHq_API
            api = TdxHq_API(heartbeat=True, auto_retry=True)
            api.connect()
            try:
                data = api.get_security_quotes([(market, code)])
                if not data:
                    return format_error_response("PYTDX_NO_DATA")
                d = data[0]
                price = d.get("price", 0) or 0
                prev_close = d.get("close", 0) or 0
                change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0
                return {
                    "source": self.name,
                    "market": market,
                    "code": code,
                    "name": d.get("name", ERROR_MESSAGE),
                    "price": price,
                    "change_pct": change_pct,
                    "change_amount": round(price - prev_close, 2) if price and prev_close else 0.0,
                    "open": d.get("open", 0.0) or 0.0,
                    "high": d.get("high", 0.0) or 0.0,
                    "low": d.get("low", 0.0) or 0.0,
                    "volume": d.get("vol", 0) or 0,
                    "amount": d.get("amount", 0.0) or 0.0,
                    "prev_close": prev_close,
                }
            finally:
                api.disconnect()
        except Exception as e:
            return format_error_response(f"PYTDX_ERROR: {type(e).__name__}")

    async def fetch_index_realtime(self, index_code: str) -> dict:
        if index_code not in INDEX_TDX_MAP:
            return format_error_response(f"PYTDX_UNKNOWN_INDEX: {index_code}")
        market, code = INDEX_TDX_MAP[index_code]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_quote, market, code)

    async def fetch_index_list(self) -> list[dict]:
        results = []
        loop = asyncio.get_event_loop()
        for idx_code in INDEX_TDX_MAP:
            market, code = INDEX_TDX_MAP[idx_code]
            r = await loop.run_in_executor(None, self._get_quote, market, code)
            results.append(r)
        return results

    async def fetch_stock_realtime(self, stock_code: str, market: int = 0) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_quote, str(market), stock_code)

    async def health_check(self) -> bool:
        try:
            from pytdx.hq import TdxHq_API
            api = TdxHq_API()
            api.connect(timeout=3)
            api.disconnect()
            return True
        except Exception:
            return False

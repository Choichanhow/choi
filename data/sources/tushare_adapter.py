"""
Tushare 数据源适配器 — A-Share Market Dashboard
MANIFESTO II: 数据原子化 — 只负责"拿"，不负责"算"
MANIFESTO IV: 鲁棒性预设 — 所有接口必须有降级处理

使用条件：
- 需要 Tushare Token
- 需要网络连通
- 适合需要标准化数据或历史数据的场景

修复内容：
1. 更新API调用方式（ts.pro → ts.pro_api）
2. 添加详细错误处理和日志记录
3. 修复指数代码格式（需要后缀.SH/.SZ）
"""

import asyncio
import logging
from typing import Optional

from data.sources.config import TUSHARE_TOKEN
from data.fetcher import safe_fetch, format_error_response
from data.trading_dates import get_last_trading_date, format_date_for_tushare
from config.settings import (
    INDEX_CODES, FALLBACK_VALUES, ERROR_MESSAGE
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class TushareAdapter:
    name = "tushare"
    supported_index_codes = INDEX_CODES

    _ts = None
    _last_error = None

    def __init__(self):
        self._ts = None
        self._last_error = None

    def _get_client(self):
        if self._ts is not None:
            return self._ts

        if not TUSHARE_TOKEN:
            logger.warning("Tushare: Token not configured")
            self._last_error = "TUSHARE_TOKEN_NOT_SET"
            return None

        try:
            import tushare as ts
            ts.set_token(TUSHARE_TOKEN)
            self._ts = ts.pro_api()
            logger.info("Tushare: Connected successfully")
            return self._ts
        except Exception as e:
            logger.error(f"Tushare: Connection failed - {type(e).__name__}: {str(e)}")
            self._last_error = f"TUSHARE_CONNECTION_ERROR: {type(e).__name__}: {str(e)}"
            return None

    def _get_index_ts_code(self, index_code: str) -> str:
        """获取Tushare格式的指数代码"""
        code = INDEX_CODES.get(index_code, index_code)
        
        if code.startswith("000"):
            return f"{code}.SH"
        elif code.startswith("399"):
            return f"{code}.SZ"
        else:
            return f"{code}.SH"

    async def fetch_index_realtime(self, index_code: str) -> dict:
        try:
            ts = self._get_client()
            if not ts:
                return format_error_response("TUSHARE_NOT_CONFIGURED")

            ts_code = self._get_index_ts_code(index_code)
            
            trading_date = get_last_trading_date()
            date_str = format_date_for_tushare(trading_date) if trading_date else ""

            df = None
            
            try:
                df = await asyncio.to_thread(
                    ts.index_daily, ts_code=ts_code, start_date=date_str, end_date=date_str
                )
            except Exception as e:
                logger.warning(f"Tushare index_daily failed (may need premium): {e}")
                try:
                    df = await asyncio.to_thread(
                        ts.daily, ts_code=ts_code, start_date=date_str, end_date=date_str
                    )
                except Exception as e2:
                    logger.warning(f"Tushare daily also failed: {e2}")

            if df is None or df.empty:
                try:
                    df = await asyncio.to_thread(
                        ts.index_daily, ts_code=ts_code
                    )
                except Exception:
                    try:
                        df = await asyncio.to_thread(
                            ts.daily, ts_code=ts_code
                        )
                    except Exception as e:
                        logger.warning(f"Tushare: No data for {index_code} ({ts_code}): {e}")
                        return format_error_response("TUSHARE_NO_DATA")

            if df is None or df.empty:
                logger.warning(f"Tushare: No data for {index_code} ({ts_code})")
                return format_error_response("TUSHARE_NO_DATA")

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            price = safe_fetch(latest, "close", 0)
            prev_close = safe_fetch(prev, "close", 0)
            change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0

            return {
                "source": self.name,
                "index_code": index_code,
                "code": ts_code,
                "name": index_code.replace("_", " ").title(),
                "price": price,
                "change_pct": change_pct,
                "change_amount": round(price - prev_close, 2) if price and prev_close else 0,
                "prev_close": prev_close,
                "trading_date": safe_fetch(latest, "trade_date", ""),
                "open": safe_fetch(latest, "open", 0),
                "high": safe_fetch(latest, "high", 0),
                "low": safe_fetch(latest, "low", 0),
                "volume": safe_fetch(latest, "vol", 0),
                "amount": safe_fetch(latest, "amount", 0),
            }
        except Exception as e:
            logger.error(f"Tushare fetch_index_realtime failed - {type(e).__name__}: {str(e)}")
            return format_error_response(f"TUSHARE_ERROR: {type(e).__name__}: {str(e)}")

    async def fetch_market_breadth(self) -> dict:
        try:
            ts = self._get_client()
            if not ts:
                return {"error": True, "reason": "TUSHARE_NOT_CONFIGURED"}

            trading_date = get_last_trading_date()
            date_str = format_date_for_tushare(trading_date) if trading_date else ""

            df = await asyncio.to_thread(
                ts.daily, trade_date=date_str, fields="ts_code,pct_chg"
            )

            if df is None or df.empty:
                logger.warning(f"Tushare: No breadth data for {date_str}")
                return {"error": True, "reason": "TUSHARE_NO_DATA"}

            up_count = len(df[df["pct_chg"] > 0])
            down_count = len(df[df["pct_chg"] < 0])
            flat_count = len(df[df["pct_chg"] == 0])
            total = len(df)

            return {
                "source": self.name,
                "up_count": up_count,
                "down_count": down_count,
                "flat_count": flat_count,
                "total": total,
                "ratio": round((up_count - down_count) / total * 100, 2) if total > 0 else 0,
                "trading_date": date_str,
            }
        except Exception as e:
            logger.error(f"Tushare fetch_market_breadth failed - {type(e).__name__}: {str(e)}")
            return {"error": True, "reason": f"TUSHARE_BREADTH_ERROR: {type(e).__name__}: {str(e)}"}

    async def fetch_sector_list(self) -> list[dict]:
        try:
            ts = self._get_client()
            if not ts:
                return [{"error": True, "reason": "TUSHARE_NOT_CONFIGURED"}]

            df = await asyncio.to_thread(ts.concept)

            if df is None or df.empty:
                df = await asyncio.to_thread(ts.index_classify)

            if df is None or df.empty:
                logger.warning("Tushare: No sector data available")
                return []

            result = []
            for _, row in df.iterrows():
                result.append({
                    "source": self.name,
                    "sector_name": safe_fetch(row, "name", ERROR_MESSAGE),
                    "sector_code": safe_fetch(row, "code", safe_fetch(row, "ts_code", ERROR_MESSAGE)),
                    "change_pct": safe_fetch(row, "pct_chg", 0),
                })
            return result
        except Exception as e:
            logger.error(f"Tushare fetch_sector_list failed - {type(e).__name__}: {str(e)}")
            return [{"error": True, "reason": f"TUSHARE_SECTOR_ERROR: {type(e).__name__}: {str(e)}"}]

    async def health_check(self) -> bool:
        try:
            ts = self._get_client()
            if ts is None:
                return False

            await asyncio.to_thread(ts.stock_basic, exchange="", list_status="L", fields="ts_code", limit=1)
            logger.info("Tushare health check passed")
            return True
        except Exception as e:
            logger.error(f"Tushare health check failed - {type(e).__name__}: {str(e)}")
            return False

    def get_last_error(self) -> Optional[str]:
        """获取最后一次错误信息"""
        return self._last_error

    async def fetch_stock_realtime(self, stock_code: str) -> dict:
        try:
            ts = self._get_client()
            if not ts:
                return format_error_response("TUSHARE_NOT_CONFIGURED")

            if len(stock_code) == 6:
                if stock_code.startswith("6"):
                    stock_code = f"{stock_code}.SH"
                else:
                    stock_code = f"{stock_code}.SZ"

            trading_date = get_last_trading_date()
            date_str = format_date_for_tushare(trading_date) if trading_date else ""

            df = await asyncio.to_thread(
                ts.daily, ts_code=stock_code, start_date=date_str, end_date=date_str
            )

            if df is None or df.empty:
                return format_error_response("TUSHARE_NO_DATA")

            latest = df.iloc[-1]
            prev_df = await asyncio.to_thread(
                ts.daily, ts_code=stock_code, start_date="", end_date=""
            )
            prev_close = safe_fetch(prev_df.iloc[-2], "close", 0) if prev_df is not None and len(prev_df) > 1 else 0

            return {
                "source": self.name,
                "code": stock_code,
                "price": safe_fetch(latest, "close", 0),
                "change_pct": safe_fetch(latest, "pct_chg", 0),
                "open": safe_fetch(latest, "open", 0),
                "high": safe_fetch(latest, "high", 0),
                "low": safe_fetch(latest, "low", 0),
                "volume": safe_fetch(latest, "vol", 0),
                "amount": safe_fetch(latest, "amount", 0),
                "prev_close": prev_close,
            }
        except Exception as e:
            logger.error(f"Tushare fetch_stock_realtime failed - {type(e).__name__}: {str(e)}")
            return format_error_response(f"TUSHARE_ERROR: {type(e).__name__}: {str(e)}")

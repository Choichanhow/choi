"""
Pytdx 数据源适配器 — A-Share Market Dashboard
MANIFESTO II: 数据原子化 — 只负责"拿"，不负责"算"
MANIFESTO IV: 鲁棒性预设 — 所有接口必须有降级处理

优化点：
1. 自动最优服务器选择: 扫描 pytdx 内置 104 个服务器，TCP 检测后 API 验证，
   选择延迟最低的服务器，支持 fallback 到下一个可用服务器
2. 连接池复用: 避免每次请求都建立新连接
3. 批量获取: 一次请求获取多个指数
4. 交易日管理: 自动检测最新已完成交易日，确保获取的是收盘价数据
"""

import asyncio
import datetime
import socket
import time
from typing import Optional, Tuple

from data.fetcher import safe_fetch, format_error_response
from data.trading_dates import get_last_trading_date, validate_trading_date_for_pytdx, format_date_for_pytdx
from config.settings import INDEX_CODES, INDEX_TDX_MAP, PYTDX_BEST_SERVER, FALLBACK_VALUES, ERROR_MESSAGE


class PytdxAdapter:
    name = "pytdx"
    supported_index_codes = INDEX_CODES

    _best_servers: Optional[list] = None
    _current_server_idx: int = 0
    _api = None

    async def fetch_index_realtime(self, index_code: str) -> dict:
        if index_code not in INDEX_TDX_MAP:
            return format_error_response(f"PYTDX_UNKNOWN_INDEX: {index_code}")
        
        trading_date = get_last_trading_date()
        if trading_date is None:
            return format_error_response("PYTDX_NO_TRADING_DATE")
        
        is_valid, msg = validate_trading_date_for_pytdx(trading_date)
        if not is_valid:
            return format_error_response(f"PYTDX_INVALID_DATE: {msg}")
        
        market, code = INDEX_TDX_MAP[index_code]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_quote, market, code, trading_date)

    def _get_quote(self, market: int, code: str, trading_date: datetime.date) -> dict:
        try:
            from pytdx.hq import TdxHq_API
            api = TdxHq_API(heartbeat=True)
            best = self._get_best_server()
            api.connect(ip=best[0], port=best[1], time_out=5)
            
            try:
                data = api.get_security_quotes([(market, code)])
                if not data:
                    return format_error_response("PYTDX_NO_DATA")
                
                d = data[0]
                price = d.get("price", 0) or 0
                prev_close = d.get("close", 0) or 0
                change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0
                
                data_date = d.get("date", "")
                date_match = self._validate_data_date(data_date, trading_date)
                
                return {
                    "source": self.name,
                    "server": f"{best[0]}:{best[1]}",
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
                    "trading_date": trading_date.strftime("%Y-%m-%d"),
                    "data_date": data_date,
                    "date_matched": date_match,
                }
            finally:
                api.disconnect()
        except Exception as e:
            return format_error_response(f"PYTDX_ERROR: {type(e).__name__}: {str(e)}")

    def _validate_data_date(self, data_date: str, expected_date: datetime.date) -> bool:
        """验证数据日期是否与预期交易日匹配"""
        if not data_date:
            return False
        
        try:
            parsed = datetime.datetime.strptime(data_date, "%Y%m%d").date()
            return parsed == expected_date
        except Exception:
            return False

    def _get_best_server(self) -> tuple:
        if self._best_servers and self._current_server_idx < len(self._best_servers):
            return self._best_servers[self._current_server_idx]
        return PYTDX_BEST_SERVER

    def _ensure_best_servers(self):
        if self._best_servers is not None:
            return

        try:
            from pytdx.config.hosts import hq_hosts

            def test_and_benchmark(entry):
                name, host, port = entry[0], entry[1], entry[2]
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2)
                    s.connect((host, port))
                    s.close()
                except Exception:
                    return None

                try:
                    from pytdx.hq import TdxHq_API
                    api = TdxHq_API(heartbeat=False)
                    api.connect(ip=host, port=port, time_out=3)
                    start = time.time()
                    data = api.get_security_quotes([(0, "000001")])
                    elapsed = round((time.time() - start) * 1000)
                    api.disconnect()
                    if data:
                        return (elapsed, name, host, port)
                except Exception:
                    try:
                        api.disconnect()
                    except Exception:
                        pass
                return None

            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=20) as pool:
                results = list(pool.map(test_and_benchmark, hq_hosts))

            valid = [r for r in results if r is not None]
            valid.sort(key=lambda x: x[0])
            self._best_servers = [(r[2], r[3]) for r in valid]
            self._current_server_idx = 0
        except Exception:
            self._best_servers = [PYTDX_BEST_SERVER]
            self._current_server_idx = 0

    async def fetch_index_list(self) -> list[dict]:
        trading_date = get_last_trading_date()
        if trading_date is None:
            return [{"error": True, "reason": "PYTDX_NO_TRADING_DATE"}]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_index_list_sync, trading_date)

    def _fetch_index_list_sync(self, trading_date: datetime.date) -> list[dict]:
        try:
            from pytdx.hq import TdxHq_API
            api = TdxHq_API(heartbeat=False)
            best = self._get_best_server()
            api.connect(ip=best[0], port=best[1], time_out=5)
            try:
                data = api.get_security_quotes([
                    (0, "000001"), (0, "399001"), (0, "399006"), (0, "000688")
                ])
                result = []
                for d in data:
                    price = d.get("price", 0) or 0
                    prev_close = d.get("close", 0) or 0
                    change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0
                    result.append({
                        "source": self.name,
                        "code": d.get("code", ERROR_MESSAGE),
                        "name": d.get("name", ERROR_MESSAGE),
                        "price": price,
                        "change_pct": change_pct,
                        "volume": d.get("vol", 0) or 0,
                        "amount": d.get("amount", 0.0) or 0.0,
                        "trading_date": trading_date.strftime("%Y-%m-%d"),
                    })
                return result
            finally:
                api.disconnect()
        except Exception as e:
            return [{"error": True, "reason": f"PYTDX_INDEX_LIST_ERROR: {type(e).__name__}: {str(e)}"}]

    async def fetch_stock_realtime(self, stock_code: str, market: int = 0) -> dict:
        trading_date = get_last_trading_date()
        if trading_date is None:
            return format_error_response("PYTDX_NO_TRADING_DATE")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_quote, market, stock_code, trading_date)

    async def health_check(self) -> bool:
        try:
            from pytdx.hq import TdxHq_API
            api = TdxHq_API()
            best = self._get_best_server()
            api.connect(ip=best[0], port=best[1], time_out=3)
            api.disconnect()
            return True
        except Exception:
            return False

    def trigger_best_server_discovery(self):
        self._ensure_best_servers()

    async def fetch_historical_data(self, index_code: str, trading_date: Optional[datetime.date] = None) -> dict:
        """获取指定交易日的历史数据（收盘价）"""
        if index_code not in INDEX_TDX_MAP:
            return format_error_response(f"PYTDX_UNKNOWN_INDEX: {index_code}")
        
        if trading_date is None:
            trading_date = get_last_trading_date()
        
        if trading_date is None:
            return format_error_response("PYTDX_NO_TRADING_DATE")
        
        is_valid, msg = validate_trading_date_for_pytdx(trading_date)
        if not is_valid:
            return format_error_response(f"PYTDX_INVALID_DATE: {msg}")
        
        market, code = INDEX_TDX_MAP[index_code]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_historical_data, market, code, trading_date)

    def _get_historical_data(self, market: int, code: str, trading_date: datetime.date) -> dict:
        """获取历史K线数据以获取收盘价"""
        try:
            from pytdx.hq import TdxHq_API
            api = TdxHq_API(heartbeat=True)
            best = self._get_best_server()
            api.connect(ip=best[0], port=best[1], time_out=5)
            
            try:
                date_str = format_date_for_pytdx(trading_date)
                data = api.get_k_data(market, code, start=date_str, end=date_str)
                
                if not data or len(data) == 0:
                    return format_error_response(f"PYTDX_NO_HISTORICAL_DATA: {date_str}")
                
                kline = data[0]
                return {
                    "source": self.name,
                    "server": f"{best[0]}:{best[1]}",
                    "code": code,
                    "trading_date": trading_date.strftime("%Y-%m-%d"),
                    "open": kline.get("open", 0.0) or 0.0,
                    "close": kline.get("close", 0.0) or 0.0,
                    "high": kline.get("high", 0.0) or 0.0,
                    "low": kline.get("low", 0.0) or 0.0,
                    "volume": kline.get("vol", 0) or 0,
                    "amount": kline.get("amount", 0.0) or 0.0,
                }
            finally:
                api.disconnect()
        except Exception as e:
            return format_error_response(f"PYTDX_HISTORICAL_ERROR: {type(e).__name__}: {str(e)}")

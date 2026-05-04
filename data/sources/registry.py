"""
数据源注册中心 — A-Share Market Dashboard
提供统一的获取接口，支持 AKShare / Pytdx 双数据源切换
"""

from typing import Literal

from data.sources.akshare_adapter import AKShareAdapter
from data.sources.pytdx_adapter import PytdxAdapter

ADAPTERS = {
    "akshare": AKShareAdapter(),
    "pytdx": PytdxAdapter(),
}

DEFAULT_SOURCE: Literal["akshare", "pytdx"] = "akshare"


def get_adapter(source: str = DEFAULT_SOURCE):
    return ADAPTERS.get(source, ADAPTERS[DEFAULT_SOURCE])


async def fetch_index_realtime(index_code: str, source: str = DEFAULT_SOURCE):
    return await get_adapter(source).fetch_index_realtime(index_code)


async def fetch_sector_list(source: str = DEFAULT_SOURCE):
    return await get_adapter(source).fetch_sector_list()


async def fetch_stock_realtime(stock_code: str, source: str = DEFAULT_SOURCE):
    return await get_adapter(source).fetch_stock_realtime(stock_code)


async def fetch_zt_pool(source: str = DEFAULT_SOURCE):
    return await get_adapter(source).fetch_zt_pool()


async def health_check(source: str = DEFAULT_SOURCE) -> bool:
    return await get_adapter(source).health_check()


async def fetch_all_indices(source: str = DEFAULT_SOURCE) -> list[dict]:
    adapter = get_adapter(source)
    from config.settings import INDEX_CODES
    tasks = [adapter.fetch_index_realtime(code) for code in INDEX_CODES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]


async def fetch_all_dashboard_data(source: str = DEFAULT_SOURCE) -> dict:
    adapter = get_adapter(source)
    return await adapter.fetch_all_dashboard_data()


import asyncio

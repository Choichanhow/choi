"""
数据源注册中心 — A-Share Market Dashboard
提供统一的获取接口，支持 AKShare / Pytdx 双数据源智能切换

智能路由策略：
- 指数实时行情: Pytdx (17ms) 优先，AKShare (1s) 作为 fallback
- 板块列表/市场广度: 仅 AKShare 支持（Pytdx 无此接口）
- 涨停池: 仅 AKShare 支持（Pytdx 无此接口）
- 个股行情: AKShare（HTTP接口更稳定），Pytdx 作为备用
"""

import asyncio
from typing import Literal

from data.sources.akshare_adapter import AKShareAdapter
from data.sources.pytdx_adapter import PytdxAdapter

ADAPTERS = {
    "akshare": AKShareAdapter(),
    "pytdx": PytdxAdapter(),
}

DEFAULT_SOURCE: Literal["akshare", "pytdx"] = "akshare"

PYTDX_ENABLED = True


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


async def get_best_index_data(index_code: str) -> dict:
    if PYTDX_ENABLED:
        try:
            pytdx_result = await ADAPTERS["pytdx"].fetch_index_realtime(index_code)
            if "error" not in pytdx_result:
                return pytdx_result
        except Exception:
            pass

    akshare_result = await ADAPTERS["akshare"].fetch_index_realtime(index_code)
    return akshare_result


async def get_smart_dashboard_data() -> dict:
    akshare_adapter = ADAPTERS["akshare"]

    index_tasks = [
        get_best_index_data("shanghai"),
        get_best_index_data("shenzhen"),
        get_best_index_data("chinext"),
    ]
    sh, sz, cy = await asyncio.gather(*index_tasks, return_exceptions=True)

    breadth = await akshare_adapter.fetch_market_breadth()
    sectors = await akshare_adapter.fetch_sector_list()

    top_sectors = sorted(
        [s for s in sectors if "error" not in s],
        key=lambda x: x.get("change_pct", 0) or 0,
        reverse=True
    )[:10]

    return {
        "indices": {
            "shanghai": sh if not isinstance(sh, Exception) else {"error": True},
            "shenzhen": sz if not isinstance(sz, Exception) else {"error": True},
            "chinext": cy if not isinstance(cy, Exception) else {"error": True},
        },
        "market_breadth": breadth,
        "top_sectors": top_sectors,
    }

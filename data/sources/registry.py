"""
数据源注册中心 — A-Share Market Dashboard
提供统一的获取接口，支持 AKShare / Pytdx 双数据源智能切换

智能路由策略（修复版）：
- Pytdx 暂时禁用（数据解析问题）
- 所有数据使用 AKShare（数据准确）
"""

import asyncio

from data.sources.akshare_adapter import AKShareAdapter

ADAPTERS = {
    "akshare": AKShareAdapter(),
}

DEFAULT_SOURCE = "akshare"

PYTDX_ENABLED = False


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


async def get_best_index_data(index_code: str) -> dict:
    return await ADAPTERS["akshare"].fetch_index_realtime(index_code)


async def get_smart_dashboard_data() -> dict:
    akshare_adapter = ADAPTERS["akshare"]

    index_tasks = [
        get_best_index_data("shanghai"),
        get_best_index_data("shenzhen"),
        get_best_index_data("chinext"),
        get_best_index_data("star_50"),
        get_best_index_data("star_composite"),
        get_best_index_data("csi_all"),
    ]
    sh, sz, cy, star, star_com, csi_all = await asyncio.gather(*index_tasks, return_exceptions=True)

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
            "star_50": star if not isinstance(star, Exception) else {"error": True},
            "star_composite": star_com if not isinstance(star_com, Exception) else {"error": True},
            "csi_all": csi_all if not isinstance(csi_all, Exception) else {"error": True},
        },
        "market_breadth": breadth,
        "top_sectors": top_sectors,
    }

"""
数据源注册中心 — A-Share Market Dashboard
提供统一的获取接口，支持多数据源智能切换

支持的数权策略：
- akshare: AKShare（默认，无需Token）
- tushare: Tushare（需要Token）
- mysql: MySQL本地库（需要配置）
- postgresql: PostgreSQL本地库（需要配置）

优先使用顺序：
1. 如果配置了本地数据库（MySQL/PostgreSQL），优先使用（最低延迟）
2. 如果配置了Tushare Token，使用Tushare（标准化数据）
3. 默认使用AKShare（无需配置）
"""

import asyncio

from data.sources.config import get_current_source, is_source_available
from data.sources.akshare_adapter import AKShareAdapter
from data.sources.tushare_adapter import TushareAdapter

ADAPTERS = {
    "akshare": AKShareAdapter(),
}

if is_source_available("tushare"):
    ADAPTERS["tushare"] = TushareAdapter()

DEFAULT_SOURCE = get_current_source()


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


async def get_fast_indices_data() -> dict:
    index_tasks = [
        get_best_index_data("shanghai"),
        get_best_index_data("shenzhen"),
        get_best_index_data("chinext"),
        get_best_index_data("star_50"),
        get_best_index_data("star_composite"),
        get_best_index_data("csi_all"),
    ]
    results = await asyncio.gather(*index_tasks, return_exceptions=True)

    index_keys = ["shanghai", "shenzhen", "chinext", "star_50", "star_composite", "csi_all"]
    indices = {}
    for i, r in enumerate(results):
        key = index_keys[i]
        indices[key] = r if not isinstance(r, Exception) else {"error": True}

    return {"indices": indices}


async def get_breadth_data() -> dict:
    return await ADAPTERS["akshare"].fetch_market_breadth()


async def get_sectors_data() -> dict:
    sectors = await ADAPTERS["akshare"].fetch_sector_list()
    top_sectors = sorted(
        [s for s in sectors if "error" not in s],
        key=lambda x: x.get("change_pct", 0) or 0,
        reverse=True
    )[:10]
    return {"top_sectors": top_sectors}

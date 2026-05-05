"""
数据源注册中心 — A-Share Market Dashboard
提供统一的获取接口，支持多数据源智能切换

支持的数据源：
- local: 本地数据库（优先使用）
- akshare: AKShare（默认网络源）
- tushare: Tushare（需要Token）
- pytdx: Pytdx（需要配置）

数据访问优先级：
1. 本地数据库（数据新鲜度检查）
2. 网络接口获取
3. 保存到本地数据库
"""

import asyncio
import datetime

from data.sources.config import get_current_source, is_source_available
from data.sources.akshare_adapter import AKShareAdapter
from data.sources.tushare_adapter import TushareAdapter
from data.local_storage import (
    get_daily_index_data, save_daily_index_data,
    get_daily_market_breadth, save_daily_market_breadth,
    get_daily_sectors, save_daily_sectors,
    is_data_fresh, get_last_trading_date
)
from data.trading_dates import get_last_trading_date as get_trading_date
from config.settings import PYTDX_ENABLED

ADAPTERS = {
    "akshare": AKShareAdapter(),
}

if is_source_available("tushare"):
    ADAPTERS["tushare"] = TushareAdapter()

if PYTDX_ENABLED:
    try:
        from data.sources.pytdx_adapter import PytdxAdapter
        ADAPTERS["pytdx"] = PytdxAdapter()
    except ImportError:
        pass

DEFAULT_SOURCE = get_current_source()


def get_adapter(source: str = DEFAULT_SOURCE):
    return ADAPTERS.get(source, ADAPTERS["akshare"])


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
    trading_date = get_trading_date()
    
    local_data = get_daily_index_data(trading_date)
    if local_data:
        index_data = local_data.get(index_code)
        if index_data and not index_data.get("error"):
            return index_data
    
    data = await ADAPTERS["akshare"].fetch_index_realtime(index_code)
    
    if not data.get("error"):
        all_indices = get_daily_index_data(trading_date) or {}
        all_indices[index_code] = data
        save_daily_index_data(trading_date, all_indices)
    
    return data


async def get_smart_dashboard_data() -> dict:
    trading_date = get_trading_date()
    
    local_indices = get_daily_index_data(trading_date)
    local_breadth = get_daily_market_breadth(trading_date)
    local_sectors = get_daily_sectors(trading_date)
    
    needs_fetch = False
    if not local_indices or not local_breadth or not local_sectors:
        needs_fetch = True
    else:
        if not is_data_fresh(trading_date):
            needs_fetch = True
    
    if needs_fetch:
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

        indices_data = {
            "shanghai": sh if not isinstance(sh, Exception) else {"error": True},
            "shenzhen": sz if not isinstance(sz, Exception) else {"error": True},
            "chinext": cy if not isinstance(cy, Exception) else {"error": True},
            "star_50": star if not isinstance(star, Exception) else {"error": True},
            "star_composite": star_com if not isinstance(star_com, Exception) else {"error": True},
            "csi_all": csi_all if not isinstance(csi_all, Exception) else {"error": True},
        }

        top_sectors = sorted(
            [s for s in sectors if "error" not in s],
            key=lambda x: x.get("change_pct", 0) or 0,
            reverse=True
        )[:10]

        if trading_date:
            if not indices_data.get("error"):
                save_daily_index_data(trading_date, indices_data)
            if not breadth.get("error"):
                save_daily_market_breadth(trading_date, breadth)
            if top_sectors:
                save_daily_sectors(trading_date, top_sectors)

        return {
            "indices": indices_data,
            "market_breadth": breadth,
            "top_sectors": top_sectors,
            "data_source": "network",
            "trading_date": trading_date.strftime("%Y-%m-%d") if trading_date else None,
        }
    else:
        top_sectors = sorted(
            [s for s in local_sectors if "error" not in s],
            key=lambda x: x.get("change_pct", 0) or 0,
            reverse=True
        )[:10]

        return {
            "indices": local_indices,
            "market_breadth": local_breadth,
            "top_sectors": top_sectors,
            "data_source": "local",
            "trading_date": trading_date.strftime("%Y-%m-%d") if trading_date else None,
        }


async def get_fast_indices_data() -> dict:
    trading_date = get_trading_date()
    local_data = get_daily_index_data(trading_date)
    
    if local_data and is_data_fresh(trading_date, max_hours=6):
        return {"indices": local_data, "data_source": "local"}
    
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

    return {"indices": indices, "data_source": "network"}


async def get_breadth_data() -> dict:
    trading_date = get_trading_date()
    local_data = get_daily_market_breadth(trading_date)
    
    if local_data and is_data_fresh(trading_date, max_hours=6):
        return local_data
    
    data = await ADAPTERS["akshare"].fetch_market_breadth()
    
    if not data.get("error") and trading_date:
        save_daily_market_breadth(trading_date, data)
    
    return data


async def get_sectors_data() -> dict:
    trading_date = get_trading_date()
    local_data = get_daily_sectors(trading_date)
    
    if local_data and is_data_fresh(trading_date, max_hours=6):
        return {"top_sectors": local_data}
    
    sectors = []
    
    if "pytdx" in ADAPTERS:
        try:
            pytdx_sectors = await ADAPTERS["pytdx"].fetch_industry_sectors()
            if pytdx_sectors and len(pytdx_sectors) > 0 and "error" not in pytdx_sectors[0]:
                sectors = pytdx_sectors
            else:
                sectors = await ADAPTERS["akshare"].fetch_sector_list()
        except Exception:
            sectors = await ADAPTERS["akshare"].fetch_sector_list()
    else:
        sectors = await ADAPTERS["akshare"].fetch_sector_list()
    
    top_sectors = sorted(
        [s for s in sectors if "error" not in s],
        key=lambda x: x.get("change_pct", 0) or 0,
        reverse=True
    )
    
    if top_sectors and trading_date:
        save_daily_sectors(trading_date, top_sectors)
    
    return {"top_sectors": top_sectors}

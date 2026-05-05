"""
市场行情 API 路由 — A-Share Market Dashboard
MANIFESTO III: 视图无状态 — 路由仅负责转发数据，不处理业务逻辑

分层加载策略：
- /indices/fast: 快速获取指数数据（约2-3秒），立即返回
- /breadth/async: 单独获取市场广度（约60秒），后台加载
- /sectors/async: 单独获取板块数据（约3秒）
"""

import asyncio

from fastapi import APIRouter, HTTPException

from data.sources import registry
from logic.indicators import (
    calc_market_overview,
    calc_breadth_ratio,
    calc_sector_heat,
    calc_sector_rotation,
)

router = APIRouter(prefix="/api", tags=["market"])

API_TIMEOUT = 180.0
BREADTH_TIMEOUT = 120.0


async def _with_timeout(coro, timeout):
    return await asyncio.wait_for(coro, timeout=timeout)


@router.get("/indices/fast")
async def indices_fast():
    """快速获取指数数据，约2-3秒返回"""
    try:
        data = await _with_timeout(registry.get_fast_indices_data(), 10.0)
        return {
            k: {
                "name": v.get("name", "--"),
                "price": v.get("price", 0),
                "change_pct": v.get("change_pct", 0),
                "source": v.get("source", "unknown"),
            }
            for k, v in data.get("indices", {}).items()
            if isinstance(v, dict)
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="指数数据获取超时")


@router.get("/breadth/async")
async def breadth_async():
    """单独获取市场广度数据，约60秒返回"""
    try:
        breadth = await _with_timeout(registry.get_breadth_data(), BREADTH_TIMEOUT)
        if not breadth or "error" in breadth:
            raise HTTPException(status_code=503, detail="市场广度数据不可用")
        return calc_breadth_ratio(
            up_count=breadth.get("up_count", 0),
            down_count=breadth.get("down_count", 0),
            total=breadth.get("total", 0),
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="市场广度获取超时，请稍后重试")


@router.get("/sectors/async")
async def sectors_async(limit: int = 10):
    """单独获取板块轮动数据，约3秒返回"""
    try:
        data = await _with_timeout(registry.get_sectors_data(), 30.0)
        sectors = data.get("top_sectors", [])
        return {
            "sectors": calc_sector_rotation(sectors, top_n=limit),
            "heat": calc_sector_heat(sectors),
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="板块数据获取超时")


@router.get("/market/overview")
async def market_overview():
    try:
        raw = await _with_timeout(registry.get_smart_dashboard_data(), API_TIMEOUT)
        return calc_market_overview(raw)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="请求超时，请稍后重试")


@router.get("/indices/realtime")
async def indices_realtime():
    try:
        raw = await _with_timeout(registry.get_smart_dashboard_data(), API_TIMEOUT)
        indices = raw.get("indices", {})
        return {
            k: {
                "name": v.get("name", "--"),
                "price": v.get("price", 0),
                "change_pct": v.get("change_pct", 0),
                "source": v.get("source", "unknown"),
            }
            for k, v in indices.items()
            if isinstance(v, dict)
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="请求超时，请稍后重试")


@router.get("/market/breadth")
async def market_breadth():
    try:
        raw = await _with_timeout(registry.get_smart_dashboard_data(), API_TIMEOUT)
        breadth = raw.get("market_breadth", {})
        if not breadth or "error" in breadth:
            raise HTTPException(status_code=503, detail="市场广度数据不可用")
        return calc_breadth_ratio(
            up_count=breadth.get("up_count", 0),
            down_count=breadth.get("down_count", 0),
            total=breadth.get("total", 0),
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="请求超时，请稍后重试")


@router.get("/sectors/top")
async def sectors_top(limit: int = 10):
    try:
        raw = await _with_timeout(registry.get_smart_dashboard_data(), API_TIMEOUT)
        sectors = raw.get("top_sectors", [])
        return {
            "sectors": calc_sector_rotation(sectors, top_n=limit),
            "heat": calc_sector_heat(sectors),
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="请求超时，请稍后重试")


@router.get("/sectors/all")
async def sectors_all():
    adapter = registry.ADAPTERS["akshare"]
    sectors = await adapter.fetch_sector_list()
    if not sectors or "error" in sectors[0]:
        raise HTTPException(status_code=503, detail="板块数据不可用")
    return {
        "count": len(sectors),
        "sectors": sectors,
    }


@router.get("/zt-pool")
async def zt_pool():
    adapter = registry.ADAPTERS["akshare"]
    zt = await adapter.fetch_zt_pool()
    if not zt:
        return {"count": 0, "zt_pool": [], "message": "非交易日或无涨停数据"}
    return {"count": len(zt), "zt_pool": zt}

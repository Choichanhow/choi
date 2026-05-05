"""
市场广度指标计算层 — A-Share Market Dashboard
MANIFESTO II: 逻辑纯粹性 — 纯计算模块，不触及数据获取和UI渲染

本模块所有函数均为纯函数：
- 输入: 原始数据字典
- 输出: 计算后的指标
- 依赖: 仅 Python 标准库
"""

import statistics
from typing import Optional


def calc_breadth_ratio(up_count: int, down_count: int, total: int) -> dict:
    ratio = round((up_count - down_count) / total * 100, 2) if total > 0 else 0.0
    return {
        "up_count": up_count,
        "down_count": down_count,
        "total": total,
        "flat_count": total - up_count - down_count,
        "ratio": ratio,
        "label": _ratio_label(ratio),
        "signal": _ratio_signal(ratio),
    }


def _ratio_label(ratio: float) -> str:
    if ratio >= 10:
        return "极强多头"
    elif ratio >= 5:
        return "强势多头"
    elif ratio >= 2:
        return "偏强"
    elif ratio >= -2:
        return "均衡"
    elif ratio >= -5:
        return "偏弱"
    elif ratio >= -10:
        return "弱势空头"
    else:
        return "极弱空头"


def _ratio_signal(ratio: float) -> str:
    if ratio >= 5:
        return "BULL"
    elif ratio <= -5:
        return "BEAR"
    else:
        return "NEUTRAL"


def calc_sentiment_index(up_count: int, total: int) -> dict:
    if total == 0:
        return {"index": 0.0, "label": "无法判断", "signal": "NEUTRAL"}
    index = round(up_count / total * 100, 2)
    if index >= 70:
        label, signal = "极度乐观", "EXTREME_BULL"
    elif index >= 60:
        label, signal = "乐观", "BULL"
    elif index >= 45:
        label, signal = "中性偏多", "SLIGHT_BULL"
    elif index >= 40:
        label, signal = "中性偏空", "SLIGHT_BEAR"
    elif index >= 30:
        label, signal = "悲观", "BEAR"
    else:
        label, signal = "极度悲观", "EXTREME_BEAR"
    return {"index": index, "label": label, "signal": signal}


def calc_sector_heat(sectors: list[dict]) -> dict:
    if not sectors:
        return {"heat_score": 0, "label": "无数据", "signal": "NEUTRAL"}

    rising = [s for s in sectors if (s.get("change_pct") or 0) > 0]
    falling = [s for s in sectors if (s.get("change_pct") or 0) < 0]

    avg_chg = statistics.mean([s.get("change_pct") or 0 for s in sectors])

    strong_count = len([s for s in sectors if (s.get("change_pct") or 0) >= 3])
    weak_count = len([s for s in sectors if (s.get("change_pct") or 0) <= -3])

    heat_score = round(
        len(rising) / max(len(rising) + len(falling), 1) * 50
        + strong_count / max(len(sectors), 1) * 30
        + avg_chg / 10 * 20,
        2
    )

    if heat_score >= 70:
        label, signal = "极度活跃", "EXTREME_BULL"
    elif heat_score >= 55:
        label, signal = "活跃", "BULL"
    elif heat_score >= 45:
        label, signal = "中性", "NEUTRAL"
    elif heat_score >= 30:
        label, signal = "冷清", "BEAR"
    else:
        label, signal = "极度冷清", "EXTREME_BEAR"

    return {
        "heat_score": heat_score,
        "rising_sectors": len(rising),
        "falling_sectors": len(falling),
        "avg_change_pct": round(avg_chg, 2),
        "strong_sectors": strong_count,
        "weak_sectors": weak_count,
        "label": label,
        "signal": signal,
    }


def calc_market_intensity(breadth: dict, sectors: list[dict]) -> dict:
    ratio_signal = breadth.get("signal", "NEUTRAL")
    heat = calc_sector_heat(sectors)
    heat_signal = heat.get("signal", "NEUTRAL")

    if ratio_signal == heat_signal == "EXTREME_BULL":
        overall, signal = "极强做多", "STRONG_BULL"
    elif ratio_signal == heat_signal == "BULL" or ratio_signal == "EXTREME_BULL":
        overall, signal = "做多", "BULL"
    elif ratio_signal == heat_signal == "BEAR" or ratio_signal == "EXTREME_BEAR":
        overall, signal = "做空", "BEAR"
    elif ratio_signal == "NEUTRAL" or heat_signal == "NEUTRAL":
        overall, signal = "观望", "NEUTRAL"
    else:
        overall, signal = "分歧", "DIVERGENCE"

    return {
        "overall": overall,
        "signal": signal,
        "breadth_signal": ratio_signal,
        "sector_heat_signal": heat_signal,
        "breadth_label": breadth.get("label", "--"),
        "sector_heat_label": heat.get("label", "--"),
    }


def calc_sector_rotation(sectors: list[dict], top_n: int = 10) -> list[dict]:
    if not sectors:
        return []

    sorted_sectors = sorted(
        sectors, key=lambda x: x.get("change_pct") or 0, reverse=True
    )

    result = []
    for rank, s in enumerate(sorted_sectors[:top_n], 1):
        change_pct = s.get("change_pct") or 0
        lead_pct = s.get("lead_change_pct") or 0

        momentum = round(
            change_pct * 0.6 + lead_pct * 0.4, 2
        )

        result.append({
            "rank": rank,
            "sector_name": s.get("sector_name", "--"),
            "change_pct": change_pct,
            "up_count": s.get("up_count", 0),
            "down_count": s.get("down_count", 0),
            "lead_stock": s.get("lead_stock", "--"),
            "lead_change_pct": lead_pct,
            "momentum": momentum,
            "amount": s.get("amount", 0),
            "signal": "UP" if change_pct > 0 else "DOWN",
        })
    return result


def calc_index_composite(indices: dict) -> dict:
    if not indices:
        return {"composite_change": 0.0, "signal": "NEUTRAL"}

    changes = []
    for idx_data in indices.values():
        if isinstance(idx_data, dict) and "change_pct" in idx_data:
            changes.append(idx_data.get("change_pct", 0))

    if not changes:
        return {"composite_change": 0.0, "signal": "NEUTRAL"}

    composite = round(statistics.mean(changes), 2)
    signal = "BULL" if composite > 0.5 else "BEAR" if composite < -0.5 else "NEUTRAL"

    return {"composite_change": composite, "signal": signal}


def calc_market_overview(raw_data: dict) -> dict:
    indices = raw_data.get("indices", {})
    market_breadth = raw_data.get("market_breadth", {})
    sectors = raw_data.get("top_sectors", [])

    breadth_result = calc_breadth_ratio(
        up_count=market_breadth.get("up_count", 0),
        down_count=market_breadth.get("down_count", 0),
        total=market_breadth.get("total", 0),
    )

    sentiment = calc_sentiment_index(
        up_count=market_breadth.get("up_count", 0),
        total=market_breadth.get("total", 0),
    )

    sector_heat = calc_sector_heat(sectors)
    intensity = calc_market_intensity(breadth_result, sectors)
    rotation = calc_sector_rotation(sectors, top_n=10)
    composite = calc_index_composite(indices)

    return {
        "timestamp": _now_timestamp(),
        "indices": {
            k: {
                "name": v.get("name", "--"),
                "price": v.get("price", 0),
                "change_pct": v.get("change_pct", 0),
                "source": v.get("source", "unknown"),
            }
            for k, v in indices.items()
            if isinstance(v, dict)
        },
        "market_breadth": breadth_result,
        "sentiment": sentiment,
        "sector_heat": sector_heat,
        "market_intensity": intensity,
        "sector_rotation": rotation,
        "index_composite": composite,
    }


def _now_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

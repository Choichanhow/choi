"""
指标计算层 — A-Share Market Dashboard
MANIFESTO II: 逻辑纯粹性 — 独立模块，可输出到网页 / PPT / 终端
MANIFESTO IV: 代码整洁度 — 函数短小，可读性高
"""

from typing import Optional


def calc_change_pct(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)


def calc_median(values: list[float]) -> Optional[float]:
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return round((sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2, 2)
    return round(sorted_values[n // 2], 2)


def calc_advance_decline_ratio(up_count: int, down_count: int) -> Optional[float]:
    total = up_count + down_count
    if total == 0:
        return None
    return round((up_count - down_count) / total * 100, 2)


def classify_trend(change_pct: Optional[float]) -> str:
    if change_pct is None:
        return "neutral"
    if change_pct > 0:
        return "up"
    if change_pct < 0:
        return "down"
    return "neutral"


def calc_market_breadth(stocks_data: list[dict]) -> dict:
    if not stocks_data:
        return {"up_count": 0, "down_count": 0, "flat_count": 0, "ratio": None}

    up_count = sum(1 for s in stocks_data if (s.get("change_pct") or 0) > 0)
    down_count = sum(1 for s in stocks_data if (s.get("change_pct") or 0) < 0)
    flat_count = len(stocks_data) - up_count - down_count
    ratio = calc_advance_decline_ratio(up_count, down_count)

    return {"up_count": up_count, "down_count": down_count, "flat_count": flat_count, "ratio": ratio}

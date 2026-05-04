"""
数据获取基类 — A-Share Market Dashboard
MANIFESTO II: 数据原子化 — 只负责"拿"，不负责"算"
MANIFESTO IV: 鲁棒性预设 — 所有函数必须具备优雅的降级处理
"""

from config.settings import FALLBACK_VALUES, ERROR_MESSAGE


class DataFetcher:
    """数据获取抽象基类，所有数据源适配器必须继承此类"""

    async def fetch_index_data(self, index_code: str):
        raise NotImplementedError

    async def fetch_sector_data(self):
        raise NotImplementedError

    async def fetch_stock_data(self, codes: list[str]):
        raise NotImplementedError

    async def health_check(self) -> bool:
        raise NotImplementedError


def safe_fetch(result, field: str, default=None):
    """通用安全取值，防止 KeyError / TypeError 导致崩溃"""
    if default is None:
        default = FALLBACK_VALUES.get(field, None)
    try:
        if isinstance(result, dict):
            return result.get(field, default)
        return getattr(result, field, default)
    except Exception:
        return default


def format_error_response(reason: str = "DATA_SOURCE_ERROR") -> dict:
    return {
        "error": True,
        "reason": reason,
        "price": ERROR_MESSAGE,
        "change_pct": ERROR_MESSAGE,
    }

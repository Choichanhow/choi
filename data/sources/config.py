"""
数据源配置管理器 — A-Share Market Dashboard
MANIFESTO IV: 配置驱动 — 所有参数来自配置文件

支持的数据源：
- akshare: AKShare（默认，无需Token）
- tushare: Tushare（需要Token）
- mysql: MySQL本地库（需要配置连接）
- postgresql: PostgreSQL本地库（需要配置连接）
"""

import os
from dotenv import load_dotenv

load_dotenv()

DATA_SOURCE = os.getenv("DATA_SOURCE", "akshare")

TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "stock"),
}

POSTGRESQL_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "database": os.getenv("POSTGRES_DATABASE", "stock"),
}

DATA_SOURCE_CONFIG = {
    "source": DATA_SOURCE,
    "akshare": {"enabled": True},
    "tushare": {"enabled": bool(TUSHARE_TOKEN), "token": TUSHARE_TOKEN},
    "mysql": {"enabled": os.getenv("MYSQL_ENABLED", "false").lower() == "true", **MYSQL_CONFIG},
    "postgresql": {"enabled": os.getenv("POSTGRES_ENABLED", "false").lower() == "true", **POSTGRESQL_CONFIG},
}


def get_available_sources():
    sources = []
    for name, config in DATA_SOURCE_CONFIG.items():
        if name == "source":
            continue
        if isinstance(config, dict) and config.get("enabled"):
            sources.append(name)
    return sources


def get_current_source():
    return DATA_SOURCE


def is_source_available(source_name: str) -> bool:
    if source_name == "akshare":
        return True
    config = DATA_SOURCE_CONFIG.get(source_name, {})
    return config.get("enabled", False)

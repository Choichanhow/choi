"""
交易日日期管理模块 — A-Share Market Dashboard
MANIFESTO IV: 鲁棒性预设 — 处理假期、非交易时段等边界情况

功能：
1. 自动检测最新已完成交易日
2. 验证交易日数据有效性
3. 处理假期和非交易时段场景
"""

import datetime
import os
from typing import Optional, Tuple

import akshare as ak
import pandas as pd

CACHE_DIR = "data/cache"


def _get_trading_dates_from_akshare() -> pd.DataFrame:
    """从AKShare获取交易日历"""
    try:
        df = ak.tool_trade_date_hist_sina()
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()


def get_last_trading_date(date: Optional[datetime.date] = None) -> Optional[datetime.date]:
    """
    获取最新已完成的交易日
    
    Args:
        date: 指定日期，默认为今天
        
    Returns:
        最新已完成的交易日日期，如果无法获取则返回None
    """
    if date is None:
        date = datetime.date.today()
    
    df = _get_trading_dates_from_akshare()
    if df.empty:
        return _fallback_trading_date(date)
    
    try:
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d').dt.date
        df = df.sort_values('trade_date', ascending=False)
        
        for trade_date in df['trade_date']:
            if trade_date <= date:
                return trade_date
    except Exception:
        pass
    
    return _fallback_trading_date(date)


def _fallback_trading_date(date: datetime.date) -> datetime.date:
    """
    备用交易日计算逻辑
    
    如果无法获取交易日历，使用简单逻辑：
    - 如果是工作日且在交易时段后，返回当天
    - 否则返回上一个工作日
    """
    today = date
    current_time = datetime.datetime.now().time()
    market_close = datetime.time(15, 0)
    
    if today.weekday() >= 5:
        days_to_subtract = (today.weekday() - 4) % 7
        return today - datetime.timedelta(days=days_to_subtract)
    
    if current_time < market_close:
        yesterday = today - datetime.timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= datetime.timedelta(days=1)
        return yesterday
    
    return today


def is_trading_day(date: datetime.date) -> bool:
    """判断指定日期是否为交易日"""
    df = _get_trading_dates_from_akshare()
    if not df.empty:
        try:
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d').dt.date
            return date in df['trade_date'].values
        except Exception:
            pass
    
    return date.weekday() < 5


def get_trading_status() -> dict:
    """获取当前交易状态"""
    now = datetime.datetime.now()
    today = now.date()
    current_time = now.time()
    
    market_open = datetime.time(9, 30)
    market_close = datetime.time(15, 0)
    lunch_start = datetime.time(11, 30)
    lunch_end = datetime.time(13, 0)
    
    is_today_trading = is_trading_day(today)
    
    if not is_today_trading:
        return {
            "is_trading_day": False,
            "is_in_trading_hours": False,
            "status": "非交易日",
            "next_action": f"下一交易日: {_get_next_trading_day(today)}",
            "last_trading_date": get_last_trading_date(today)
        }
    
    is_in_hours = False
    status = "交易前"
    
    if market_open <= current_time < lunch_start:
        is_in_hours = True
        status = "上午交易中"
    elif lunch_end <= current_time < market_close:
        is_in_hours = True
        status = "下午交易中"
    elif current_time >= market_close:
        status = "今日已收盘"
    
    return {
        "is_trading_day": True,
        "is_in_trading_hours": is_in_hours,
        "status": status,
        "current_time": now.strftime("%H:%M:%S"),
        "last_trading_date": get_last_trading_date(today)
    }


def _get_next_trading_day(date: datetime.date) -> datetime.date:
    """获取下一个交易日"""
    next_day = date + datetime.timedelta(days=1)
    while next_day.weekday() >= 5 or not is_trading_day(next_day):
        next_day += datetime.timedelta(days=1)
    return next_day


def validate_trading_date_for_pytdx(date: datetime.date) -> Tuple[bool, str]:
    """
    验证交易日是否可用于Pytdx接口
    
    Returns:
        (is_valid, message)
    """
    if not is_trading_day(date):
        return False, f"{date} 不是交易日"
    
    today = datetime.date.today()
    if date > today:
        return False, f"{date} 是未来日期"
    
    return True, f"{date} 是有效的交易日"


def format_date_for_pytdx(date: datetime.date) -> str:
    """将日期格式化为Pytdx所需格式"""
    return date.strftime("%Y%m%d")


def format_date_for_tushare(date: datetime.date) -> str:
    """将日期格式化为Tushare所需格式"""
    return date.strftime("%Y%m%d")


def get_last_n_trading_dates(n: int = 5) -> list:
    """获取最近N个交易日"""
    today = datetime.date.today()
    dates = []
    current = today
    
    while len(dates) < n:
        if is_trading_day(current):
            dates.append(current)
        current -= datetime.timedelta(days=1)
    
    return dates[::-1]

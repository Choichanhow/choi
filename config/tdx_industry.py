"""
通达信一级行业板块配置 — A-Share Market Dashboard
行业板块代码参考通达信一级行业分类
"""

TDX_INDUSTRY_CODES = {
    "881001": {"name": "煤炭", "market": 1},
    "881006": {"name": "石油", "market": 1},
    "881015": {"name": "化工", "market": 1},
    "881061": {"name": "钢铁", "market": 1},
    "881070": {"name": "有色", "market": 1},
    "881090": {"name": "建材", "market": 1},
    "881105": {"name": "农林牧渔", "market": 1},
    "881129": {"name": "食品饮料", "market": 1},
    "881150": {"name": "纺织服饰", "market": 1},
    "881166": {"name": "轻工制造", "market": 1},
    "881183": {"name": "家电", "market": 1},
    "881199": {"name": "商贸", "market": 1},
    "881211": {"name": "汽车", "market": 1},
    "881230": {"name": "医药医疗", "market": 1},
    "881260": {"name": "电力设备", "market": 1},
    "881286": {"name": "国防军工", "market": 1},
    "881292": {"name": "机械设备", "market": 1},
    "881318": {"name": "电子", "market": 1},
    "881337": {"name": "通信", "market": 1},
    "881351": {"name": "计算机", "market": 1},
    "881368": {"name": "传媒", "market": 1},
    "881385": {"name": "银行", "market": 1},
    "881393": {"name": "非银金融", "market": 1},
    "881405": {"name": "建筑", "market": 1},
    "881417": {"name": "房地产", "market": 1},
    "881426": {"name": "社会服务", "market": 1},
    "881441": {"name": "交通运输", "market": 1},
    "881458": {"name": "公用事业", "market": 1},
    "881469": {"name": "环保", "market": 1},
    "881477": {"name": "综合", "market": 1},
}


def get_tdx_industry_list() -> list:
    """获取所有TDX行业板块列表"""
    return [
        {"code": code, "name": info["name"], "market": info["market"]}
        for code, info in TDX_INDUSTRY_CODES.items()
    ]


def get_industry_info(code: str) -> dict:
    """获取指定行业代码的信息"""
    return TDX_INDUSTRY_CODES.get(code, {})


def get_industry_code(name: str) -> str:
    """根据行业名称获取代码"""
    for code, info in TDX_INDUSTRY_CODES.items():
        if info["name"] == name:
            return code
    return ""

"""
Module 2 测试脚本 — 验证市场广度指标计算层
纯函数测试，无需网络连接
"""

import sys
sys.path.insert(0, "h:\\QUART")

from logic.indicators import (
    calc_breadth_ratio,
    calc_sentiment_index,
    calc_sector_heat,
    calc_market_intensity,
    calc_sector_rotation,
    calc_index_composite,
    calc_market_overview,
)


def test_breadth_ratio():
    result = calc_breadth_ratio(8721, 7509, 16230)
    assert result["up_count"] == 8721
    assert result["down_count"] == 7509
    assert result["total"] == 16230
    assert result["flat_count"] == 0
    assert result["ratio"] == round((8721 - 7509) / 16230 * 100, 2)
    assert result["signal"] == "BULL"
    print(f"  ✅ calc_breadth_ratio: ratio={result['ratio']}, label={result['label']}, signal={result['signal']}")


def test_sentiment_index():
    result = calc_sentiment_index(8721, 16230)
    assert result["index"] == round(8721 / 16230 * 100, 2)
    print(f"  ✅ calc_sentiment_index: index={result['index']}, label={result['label']}, signal={result['signal']}")


def test_sector_heat():
    sectors = [
        {"sector_name": "新能源", "change_pct": 5.2, "lead_change_pct": 9.8},
        {"sector_name": "半导体", "change_pct": 3.1, "lead_change_pct": 7.5},
        {"sector_name": "医药", "change_pct": 1.2, "lead_change_pct": 4.0},
        {"sector_name": "房地产", "change_pct": -2.1, "lead_change_pct": -0.5},
        {"sector_name": "金融", "change_pct": -0.8, "lead_change_pct": 0.5},
    ]
    result = calc_sector_heat(sectors)
    assert "heat_score" in result
    assert result["rising_sectors"] == 3
    assert result["falling_sectors"] == 2
    print(f"  ✅ calc_sector_heat: score={result['heat_score']}, label={result['label']}, avg_chg={result['avg_change_pct']}%")


def test_market_intensity():
    breadth = {"signal": "BULL", "label": "强势多头"}
    sectors = [
        {"sector_name": "新能源", "change_pct": 5.2},
        {"sector_name": "半导体", "change_pct": 3.1},
    ]
    result = calc_market_intensity(breadth, sectors)
    assert result["breadth_signal"] == "BULL"
    print(f"  ✅ calc_market_intensity: overall={result['overall']}, signal={result['signal']}")


def test_sector_rotation():
    sectors = [
        {"sector_name": "新能源", "change_pct": 5.2, "up_count": 45, "down_count": 5, "lead_stock": "宁德时代", "lead_change_pct": 9.8},
        {"sector_name": "半导体", "change_pct": 3.1, "up_count": 38, "down_count": 10, "lead_stock": "中芯国际", "lead_change_pct": 7.5},
        {"sector_name": "医药", "change_pct": -1.2, "up_count": 20, "down_count": 25, "lead_stock": "恒瑞医药", "lead_change_pct": -2.0},
    ]
    result = calc_sector_rotation(sectors, top_n=3)
    assert len(result) == 3
    assert result[0]["sector_name"] == "新能源"
    assert result[0]["rank"] == 1
    assert result[0]["momentum"] == round(5.2 * 0.6 + 9.8 * 0.4, 2)
    print(f"  ✅ calc_sector_rotation: #1={result[0]['sector_name']} momentum={result[0]['momentum']}")
    print(f"     #2={result[1]['sector_name']} momentum={result[1]['momentum']}")


def test_index_composite():
    indices = {
        "shanghai": {"change_pct": 1.2, "name": "上证指数"},
        "shenzhen": {"change_pct": -0.5, "name": "深证成指"},
        "chinext": {"change_pct": 0.8, "name": "创业板指"},
    }
    result = calc_index_composite(indices)
    expected = round((1.2 + (-0.5) + 0.8) / 3, 2)
    assert result["composite_change"] == expected
    assert result["signal"] == "NEUTRAL"
    print(f"  ✅ calc_index_composite: composite={result['composite_change']}%, signal={result['signal']}")


def test_market_overview_integration():
    raw = {
        "indices": {
            "shanghai": {"name": "上证指数", "price": 3150.0, "change_pct": 1.2, "source": "pytdx"},
            "shenzhen": {"name": "深证成指", "price": 10500.0, "change_pct": -0.5, "source": "pytdx"},
            "chinext": {"name": "创业板指", "price": 2050.0, "change_pct": 0.8, "source": "pytdx"},
        },
        "market_breadth": {"up_count": 8721, "down_count": 7509, "total": 16230},
        "top_sectors": [
            {"sector_name": "新能源", "change_pct": 5.2, "up_count": 45, "down_count": 5, "lead_stock": "宁德时代", "lead_change_pct": 9.8},
            {"sector_name": "半导体", "change_pct": 3.1, "up_count": 38, "down_count": 10, "lead_stock": "中芯国际", "lead_change_pct": 7.5},
        ],
    }
    result = calc_market_overview(raw)
    assert "timestamp" in result
    assert "market_breadth" in result
    assert "sentiment" in result
    assert "sector_heat" in result
    assert "market_intensity" in result
    assert "sector_rotation" in result
    assert "index_composite" in result
    print(f"  ✅ calc_market_overview 集成测试通过")
    print(f"     breadth: ratio={result['market_breadth']['ratio']}, label={result['market_breadth']['label']}")
    print(f"     sentiment: index={result['sentiment']['index']}, label={result['sentiment']['label']}")
    print(f"     sector_heat: score={result['sector_heat']['heat_score']}, label={result['sector_heat']['label']}")
    print(f"     market_intensity: overall={result['market_intensity']['overall']}")
    print(f"     sector_rotation #1: {result['sector_rotation'][0]['sector_name']} (momentum={result['sector_rotation'][0]['momentum']})")
    print(f"     index_composite: {result['index_composite']['composite_change']}%")


def main():
    print("=" * 60)
    print("Module 2 测试 — 市场广度指标计算层")
    print("=" * 60)
    test_breadth_ratio()
    test_sentiment_index()
    test_sector_heat()
    test_market_intensity()
    test_sector_rotation()
    test_index_composite()
    test_market_overview_integration()
    print("=" * 60)
    print("✅ 所有测试通过 — logic 层已就绪")
    print("=" * 60)


if __name__ == "__main__":
    main()

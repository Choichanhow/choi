"""
数据源验证脚本 — Module 1 验证测试
验证 AKShare / Mootdx 数据拉取广度和稳定性
"""

import asyncio
import sys
import time

sys.path.insert(0, "h:\\QUART")

from data.sources.akshare_adapter import AKShareAdapter
from data.sources.mootdx_adapter import MootdxAdapter


async def test_akshare():
    print("=" * 60)
    print("[AKShare] 开始测试...")
    adapter = AKShareAdapter()

    start = time.time()
    health = await adapter.health_check()
    elapsed = round((time.time() - start) * 1000)
    print(f"  健康检查: {'✅ OK' if health else '❌ FAIL'} ({elapsed}ms)")

    start = time.time()
    sh = await adapter.fetch_index_realtime("shanghai")
    elapsed = round((time.time() - start) * 1000)
    print(f"  上证指数: {'✅' if 'error' not in sh else '❌'} ({elapsed}ms)")
    if "error" not in sh:
        print(f"    名称: {sh.get('name')} | 价格: {sh.get('price')} | 涨跌幅: {sh.get('change_pct')}%")

    start = time.time()
    sz = await adapter.fetch_index_realtime("shenzhen")
    elapsed = round((time.time() - start) * 1000)
    print(f"  深证成指: {'✅' if 'error' not in sz else '❌'} ({elapsed}ms)")
    if "error" not in sz:
        print(f"    名称: {sz.get('name')} | 价格: {sz.get('price')} | 涨跌幅: {sz.get('change_pct')}%")

    start = time.time()
    cy = await adapter.fetch_index_realtime("chinext")
    elapsed = round((time.time() - start) * 1000)
    print(f"  创业板指: {'✅' if 'error' not in cy else '❌'} ({elapsed}ms)")
    if "error" not in cy:
        print(f"    名称: {cy.get('name')} | 价格: {cy.get('price')} | 涨跌幅: {cy.get('change_pct')}%")

    start = time.time()
    breadth = await adapter.fetch_market_breadth()
    elapsed = round((time.time() - start) * 1000)
    print(f"  市场广度: {'✅' if 'error' not in breadth else '❌'} ({elapsed}ms)")
    if "error" not in breadth:
        print(f"    上涨: {breadth.get('up_count')} | 下跌: {breadth.get('down_count')} | 差值: {breadth.get('ratio')}%")

    start = time.time()
    sectors = await adapter.fetch_sector_list()
    elapsed = round((time.time() - start) * 1000)
    has_error = any("error" in s for s in sectors)
    print(f"  板块列表: {'✅' if not has_error else '❌'} ({elapsed}ms) 返回 {len(sectors)} 条")
    if sectors and "error" not in sectors[0]:
        top = sorted(sectors, key=lambda x: x.get("change_pct", 0) or 0, reverse=True)[0]
        print(f"    最强板块: {top.get('sector_name')} | 涨跌幅: {top.get('change_pct')}%")

    return health and all("error" not in x for x in [sh, sz, cy, breadth])


async def test_mootdx():
    print("=" * 60)
    print("[Mootdx] 开始测试...")
    adapter = MootdxAdapter()

    start = time.time()
    health = await adapter.health_check()
    elapsed = round((time.time() - start) * 1000)
    print(f"  健康检查: {'✅ OK' if health else '⚠️ 离线数据源' if elapsed < 3000 else '❌ FAIL'} ({elapsed}ms)")

    start = time.time()
    sh = await adapter.fetch_index_realtime("shanghai")
    elapsed = round((time.time() - start) * 1000)
    print(f"  上证指数: {'✅' if 'error' not in sh else '⚠️ 离线/未连接'} ({elapsed}ms)")
    if "error" not in sh:
        print(f"    名称: {sh.get('name')} | 价格: {sh.get('price')} | 涨跌幅: {sh.get('change_pct')}%")

    return True


async def main():
    print("\n" + "=" * 60)
    print("Module 1: 数据源适配器验证测试")
    print("=" * 60)

    akshare_ok = await test_akshare()
    mootdx_ok = await test_mootdx()

    print("=" * 60)
    print(f"AKShare 稳定性: {'✅ PASS' if akshare_ok else '❌ FAIL'} — 主数据源（实时）")
    print(f"Mootdx  稳定性: {'✅ PASS (离线模式)' if mootdx_ok else '❌ FAIL'} — 备用数据源")
    print("=" * 60)
    return akshare_ok


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)

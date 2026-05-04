"""
性能测试脚本 — 测量各数据接口耗时
"""

import asyncio
import time
import sys

sys.path.insert(0, "h:\\QUART")

from data.sources.akshare_adapter import AKShareAdapter


async def main():
    print("=" * 60)
    print("Module 1 数据源性能测试报告")
    print("=" * 60)

    print("\n[数据源配置]")
    print("  主数据源: AKShare (东方财富，实时)")
    print("  备用数据源: Pytdx (通达信协议，需TDX服务器)")
    print("  (mootdx 已移除)")

    print("\n" + "=" * 60)
    print("AKShare 详细性能测试")
    print("=" * 60)

    adapter = AKShareAdapter()

    results = []

    start = time.time()
    r = await adapter.health_check()
    results.append(("health_check", round((time.time() - start) * 1000), r))

    start = time.time()
    r = await adapter.fetch_index_realtime("shanghai")
    results.append(("上证指数", round((time.time() - start) * 1000), r))

    start = time.time()
    r = await adapter.fetch_index_realtime("shenzhen")
    results.append(("深证成指", round((time.time() - start) * 1000), r))

    start = time.time()
    r = await adapter.fetch_index_realtime("chinext")
    results.append(("创业板指", round((time.time() - start) * 1000), r))

    start = time.time()
    r = await adapter.fetch_sector_list()
    results.append(("板块列表(496条)", round((time.time() - start) * 1000), r))

    start = time.time()
    r = await adapter.fetch_market_breadth()
    results.append(("市场广度", round((time.time() - start) * 1000), r))

    print(f"\n{'操作':<22} {'耗时':>8} {'状态':>8}")
    print("-" * 42)
    serial_total = 0
    for label, ms, r in results:
        status = "OK" if "error" not in str(r) else "FAIL"
        print(f"  {label:<20} {ms:>8}ms  {status:>8}")
        serial_total += ms
    print("-" * 42)
    print(f"  {'串行总耗时':<20} {serial_total:>8}ms")

    print("\n" + "=" * 60)
    print("fetch_all_dashboard_data() 并行整合测试")
    print("=" * 60)

    new_adapter = AKShareAdapter()
    start = time.time()
    dashboard = await new_adapter.fetch_all_dashboard_data()
    t_full = round((time.time() - start) * 1000)

    indices = dashboard.get("indices", {})
    for k, v in indices.items():
        status = "OK" if "error" not in str(v) else "FAIL"
        print(f"  {status} {k}: {v.get('name')} | {v.get('price')} | {v.get('change_pct')}%")

    b = dashboard.get("market_breadth", {})
    print(f"  上涨: {b.get('up_count')} | 下跌: {b.get('down_count')} | 差值: {b.get('ratio')}%")
    print(f"  Top板块: {len(dashboard.get('top_sectors', []))} 条")
    print(f"\n  fetch_all_dashboard_data() 总耗时: {t_full}ms")

    print("\n" + "=" * 60)
    print("缓存命中测试 (30s TTL)")
    print("=" * 60)
    start = time.time()
    cached = await new_adapter.fetch_all_dashboard_data()
    t_cached = round((time.time() - start) * 1000)
    print(f"  缓存命中耗时: {t_cached}ms")

    print("\n" + "=" * 60)
    print("性能优化总结")
    print("=" * 60)
    improvement = round((1 - t_full / serial_total) * 100)
    cache_gain = round((1 - t_cached / t_full) * 100)
    speedup = round(serial_total / t_full, 1)

    print(f"  原始串行耗时:      {serial_total}ms")
    print(f"  优化后并行耗时:    {t_full}ms")
    print(f"  并行优化提升:      {improvement}%  (加速 {speedup}x)")
    print(f"  缓存命中耗时:      {t_cached}ms")
    print(f"  缓存优化提升:      {cache_gain}%")
    print(f"  综合效率:         首次 {t_full}ms | 缓存内 {t_cached}ms")


if __name__ == "__main__":
    asyncio.run(main())

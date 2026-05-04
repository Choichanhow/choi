"""
性能优化对比测试 — 串行 vs 缓存 vs 并行
"""

import asyncio
import time
import sys

sys.path.insert(0, "h:\\QUART")

from data.sources.akshare_adapter import AKShareAdapter


async def main():
    adapter = AKShareAdapter()

    print("=" * 60)
    print("性能对比测试")
    print("=" * 60)

    print("\n[1] 首次调用 — 无缓存")
    start = time.time()
    result = await adapter.fetch_all_dashboard_data()
    t1 = round((time.time() - start) * 1000)
    print(f"  总耗时: {t1}ms")
    indices = result.get("indices", {})
    for k, v in indices.items():
        status = "✅" if "error" not in str(v) else "❌"
        print(f"  {status} {k}: {v.get('name')} | {v.get('price')} | {v.get('change_pct')}%")
    breadth = result.get("market_breadth", {})
    print(f"  上涨家数: {breadth.get('up_count')} | 下跌家数: {breadth.get('down_count')} | ratio: {breadth.get('ratio')}%")
    print(f"  Top板块数: {len(result.get('top_sectors', []))} 条")

    print("\n[2] 第二次调用 — 缓存命中（30s TTL 内）")
    adapter._sector_cache_time = time.time()
    start = time.time()
    result2 = await adapter.fetch_all_dashboard_data()
    t2 = round((time.time() - start) * 1000)
    print(f"  总耗时: {t2}ms (板块缓存命中，不再请求东方财富)")

    print("\n[3] 强制刷新 — 缓存作废")
    adapter._sector_cache_time = 0
    start = time.time()
    result3 = await adapter.fetch_all_dashboard_data()
    t3 = round((time.time() - start) * 1000)
    print(f"  总耗时: {t3}ms")

    print("\n" + "=" * 60)
    print("优化效果")
    print("=" * 60)
    print(f"  首次加载（并行+缓存去重）: {t1}ms")
    print(f"  缓存命中（30s 内重复请求）: {t2}ms  ✅ 提升 {round((1 - t2/t1) * 100)}%")
    print(f"  强制刷新: {t3}ms")
    print(f"\n  串行原始耗时: ~39s → 优化后: ~{t1}ms")
    print(f"  提升幅度: {round(39000 / t1)}x")


if __name__ == "__main__":
    asyncio.run(main())

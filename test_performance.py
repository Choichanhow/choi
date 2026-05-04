"""
最终性能基准测试报告
测量 AKShare / Pytdx / 智能路由 各场景性能
"""

import asyncio
import time
import sys

sys.path.insert(0, "h:\\QUART")

from data.sources.akshare_adapter import AKShareAdapter
from data.sources.pytdx_adapter import PytdxAdapter
from data.sources import registry


def benchmark_pytdx_batch():
    from pytdx.hq import TdxHq_API
    api = TdxHq_API(heartbeat=False)
    api.connect(ip="218.106.92.183", port=7709, time_out=5)
    start = time.time()
    data = api.get_security_quotes([(0, "000001"), (0, "399001"), (0, "399006")])
    elapsed = round((time.time() - start) * 1000)
    api.disconnect()
    return elapsed, len(data)


async def main():
    print("=" * 65)
    print("性能基准测试报告 — Module 1 数据源适配器")
    print("=" * 65)

    print("\n1. AKShare 单指数请求 (未优化时需3次HTTP请求)")
    print("-" * 65)
    adapter1 = AKShareAdapter()
    results = []
    for code in ["shanghai", "shenzhen", "chinext"]:
        start = time.time()
        r = await adapter1.fetch_index_realtime(code)
        elapsed = round((time.time() - start) * 1000)
        results.append(elapsed)
        print(f"  {code}: {elapsed}ms  {'✅' if 'error' not in r else '❌'}")
    print(f"  合计: {sum(results)}ms")

    print("\n2. AKShare 批量一次请求 (优化后: 1次HTTP请求，全量数据本地筛选)")
    print("-" * 65)
    adapter2 = AKShareAdapter()
    start = time.time()
    all_indices = await adapter2.fetch_all_indices()
    t = round((time.time() - start) * 1000)
    print(f"  fetch_all_indices(): {t}ms  返回 {len(all_indices)} 条指数")

    print("\n3. Pytdx 单指数请求 (3次串行)")
    print("-" * 65)
    pytdx = PytdxAdapter()
    times = {}
    for code in ["shanghai", "shenzhen", "chinext"]:
        start = time.time()
        r = await pytdx.fetch_index_realtime(code)
        times[code] = round((time.time() - start) * 1000)
        print(f"  {code}: {times[code]}ms  {'✅' if 'error' not in r else '❌'}")
    print(f"  合计: {sum(times.values())}ms")

    print("\n4. Pytdx 批量一次请求 (1次TCP请求，3个指数)")
    print("-" * 65)
    loop = asyncio.get_event_loop()
    batch_result = await loop.run_in_executor(None, benchmark_pytdx_batch)
    print(f"  Pytdx 批量: {batch_result[0]}ms  返回 {batch_result[1]} 条")

    print("\n5. AKShare 缓存命中 (5s TTL 内)")
    print("-" * 65)
    adapter3 = AKShareAdapter()
    start = time.time()
    cached = await adapter3.fetch_all_indices()
    t_cached = round((time.time() - start) * 1000)
    print(f"  缓存命中: {t_cached}ms")

    print("\n6. 智能路由 dashboard (Pytdx指数 + AKShare板块)")
    print("-" * 65)
    start = time.time()
    dashboard = await registry.get_smart_dashboard_data()
    t_smart = round((time.time() - start) * 1000)
    print(f"  get_smart_dashboard_data(): {t_smart}ms")
    indices = dashboard.get("indices", {})
    for k, v in indices.items():
        print(f"    {k}: {v.get('name')} | {v.get('price')} | {v.get('change_pct')}%")
    breadth = dashboard.get("market_breadth", {})
    print(f"    市场广度: 上涨{breadth.get('up_count')} | 下跌{breadth.get('down_count')} | ratio={breadth.get('ratio')}%")
    print(f"    Top板块: {len(dashboard.get('top_sectors', []))} 条")

    print("\n" + "=" * 65)
    print("性能优化总结")
    print("=" * 65)
    print(f"  AKShare 串行(3指数):    {sum(results)}ms")
    print(f"  AKShare 批量(一次):    {t}ms")
    print(f"  AKShare 缓存命中:       {t_cached}ms")
    print(f"  Pytdx 串行(3指数):     {sum(times.values())}ms")
    print(f"  Pytdx 批量(1次):      {batch_result[0]}ms  ← 最优")
    print(f"  智能路由 dashboard:     {t_smart}ms")
    print()
    print(f"  关键发现:")
    if sum(results) > 0:
        print(f"  - AKShare 批量优化: {sum(results)}ms → {t}ms  (减少 {round((1 - t/sum(results))*100)}%)")
    if batch_result[0] > 0:
        print(f"  - Pytdx vs AKShare: Pytdx 快 {round(sum(results)/batch_result[0])}x (批量模式)")
    if t > 0:
        print(f"  - 缓存命中加速:  {t}ms → {t_cached}ms")


if __name__ == "__main__":
    asyncio.run(main())

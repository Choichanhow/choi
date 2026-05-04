"""
AKShare vs Pytdx 性能基准对比测试
同一功能：获取上证/深证/创业板三大指数实时数据
"""

import asyncio
import time
import sys

sys.path.insert(0, "h:\\QUART")

from data.sources.akshare_adapter import AKShareAdapter
from pytdx.hq import TdxHq_API
from config.settings import INDEX_TDX_MAP


async def benchmark_akshare():
    adapter = AKShareAdapter()
    times = {}
    for code in ["shanghai", "shenzhen", "chinext"]:
        start = time.time()
        r = await adapter.fetch_index_realtime(code)
        times[code] = round((time.time() - start) * 1000)
    return times


def benchmark_pytdx():
    api = TdxHq_API(heartbeat=False)
    api.connect(ip="218.106.92.183", port=7709, time_out=5)
    times = {}
    targets = [
        ("shanghai", 0, "000001"),
        ("shenzhen", 0, "399001"),
        ("chinext", 0, "399006"),
    ]
    for name, market, code in targets:
        start = time.time()
        data = api.get_security_quotes([(market, code)])
        times[name] = round((time.time() - start) * 1000)
    api.disconnect()
    return times


async def benchmark_pytdx_async():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, benchmark_pytdx)


async def main():
    print("=" * 60)
    print("AKShare vs Pytdx 性能基准测试")
    print("=" * 60)

    print("\n测试说明: 同一功能 = 获取三大指数实时行情")
    print("AKShare: 通过东方财富HTTP接口")
    print("Pytdx:   直连通达信服务器 (华林最优服务器)")

    print("\n" + "=" * 60)
    print("AKShare (HTTP, 东方财富)")
    print("=" * 60)

    akshare_times = await benchmark_akshare()
    for k, v in akshare_times.items():
        print(f"  {k}: {v}ms")
    akshare_total = sum(akshare_times.values())
    print(f"  总耗时: {akshare_total}ms")

    print("\n" + "=" * 60)
    print("Pytdx (TCP, 通达信协议, 17ms 服务器)")
    print("=" * 60)

    pytdx_times = await benchmark_pytdx_async()
    for k, v in pytdx_times.items():
        print(f"  {k}: {v}ms")
    pytdx_total = sum(pytdx_times.values())
    print(f"  总耗时: {pytdx_total}ms")

    print("\n" + "=" * 60)
    print("并行多指数测试 (Pytdx 一次请求获取多个)")
    print("=" * 60)

    def benchmark_pytdx_batch():
        api = TdxHq_API(heartbeat=False)
        api.connect(ip="218.106.92.183", port=7709, time_out=5)
        start = time.time()
        data = api.get_security_quotes([
            (0, "000001"), (0, "399001"), (0, "399006")
        ])
        elapsed = round((time.time() - start) * 1000)
        api.disconnect()
        return elapsed, len(data)

    loop = asyncio.get_event_loop()
    batch_result = await loop.run_in_executor(None, benchmark_pytdx_batch)
    print(f"  一次请求获取3个指数: {batch_result[0]}ms (返回 {batch_result[1]} 条数据)")

    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print(f"  AKShare 串行总耗时: {akshare_total}ms")
    print(f"  Pytdx  串行总耗时: {pytdx_total}ms")
    print(f"  Pytdx  批量(3合1):  {batch_result[0]}ms")
    print()
    if pytdx_total < akshare_total:
        ratio = round(akshare_total / pytdx_total, 1)
        print(f"  ✅ Pytdx 更快，约为 AKShare 的 {ratio}x 速度")
    else:
        ratio = round(pytdx_total / akshare_total, 1)
        print(f"  ✅ AKShare 更快，约为 Pytdx 的 {ratio}x 速度")


if __name__ == "__main__":
    asyncio.run(main())

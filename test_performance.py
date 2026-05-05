"""
性能测试脚本 — A-Share Market Dashboard
测试AKShare、Pytdx、Tushare三种数据源的性能对比
"""

import asyncio
import time
import json

async def test_akshare():
    from data.sources.akshare_adapter import AKShareAdapter
    adapter = AKShareAdapter()
    
    print("\n=== AKShare 性能测试 ===")
    
    # 测试指数数据
    start = time.time()
    result = await adapter.fetch_index_realtime("shanghai")
    elapsed = time.time() - start
    status = "成功" if "error" not in result else "失败"
    print(f"1. 指数数据: {elapsed:.2f}s [{status}]")
    
    # 测试板块数据
    start = time.time()
    result = await adapter.fetch_sector_list()
    elapsed = time.time() - start
    count = len([r for r in result if "error" not in r])
    status = "成功" if count > 0 else "失败"
    print(f"2. 板块数据: {elapsed:.2f}s [{status}, {count}个板块]")
    
    # 测试涨停池
    start = time.time()
    result = await adapter.fetch_zt_pool()
    elapsed = time.time() - start
    count = len(result) if isinstance(result, list) else 0
    status = "成功" if count > 0 else "失败"
    print(f"3. 涨停池: {elapsed:.2f}s [{status}, {count}条]")
    
    # 测试市场广度（这个比较慢）
    start = time.time()
    result = await adapter.fetch_market_breadth()
    elapsed = time.time() - start
    status = "成功" if "error" not in result else "失败"
    up_down = f"{result.get('up_count', 0)}/{result.get('down_count', 0)}" if status == "成功" else "--"
    print(f"4. 市场广度: {elapsed:.2f}s [{status}, 涨跌:{up_down}]")
    
    return {
        "akshare": {
            "index": elapsed,
            "sector": None,
            "zt_pool": None,
            "breadth": elapsed
        }
    }


async def test_pytdx():
    from data.sources.pytdx_adapter import PytdxAdapter
    adapter = PytdxAdapter()
    
    print("\n=== Pytdx 性能测试 ===")
    
    start = time.time()
    result = await adapter.fetch_index_realtime("shanghai")
    elapsed = time.time() - start
    status = "成功" if "error" not in result else "失败"
    price = result.get("price", 0)
    print(f"1. 指数数据(上海): {elapsed:.2f}s [{status}, 价格:{price}]")
    
    start = time.time()
    result = await adapter.fetch_index_realtime("shenzhen")
    elapsed = time.time() - start
    status = "成功" if "error" not in result else "失败"
    price = result.get("price", 0)
    print(f"2. 指数数据(深圳): {elapsed:.2f}s [{status}, 价格:{price}]")
    
    start = time.time()
    health = await adapter.health_check()
    elapsed = time.time() - start
    print(f"3. 健康检查: {elapsed:.2f}s [{'成功' if health else '失败'}]")
    
    return {
        "pytdx": {
            "index": elapsed,
            "health": elapsed
        }
    }


async def test_tushare():
    from data.sources.tushare_adapter import TushareAdapter
    adapter = TushareAdapter()
    
    print("\n=== Tushare 性能测试 ===")
    
    if not await adapter.health_check():
        print("Tushare未配置Token或连接失败")
        return {"tushare": {"error": "未配置或连接失败"}}
    
    start = time.time()
    result = await adapter.fetch_index_realtime("shanghai")
    elapsed = time.time() - start
    status = "成功" if "error" not in result else "失败"
    price = result.get("price", 0)
    print(f"1. 指数数据(上海): {elapsed:.2f}s [{status}, 价格:{price}]")
    
    start = time.time()
    result = await adapter.fetch_sector_list()
    elapsed = time.time() - start
    count = len([r for r in result if "error" not in r])
    status = "成功" if count > 0 else "失败"
    print(f"2. 板块数据: {elapsed:.2f}s [{status}, {count}个板块]")
    
    return {
        "tushare": {
            "index": elapsed,
            "sector": elapsed
        }
    }


async def main():
    print("="*60)
    print("A-Share Market Dashboard 数据源性能测试")
    print("="*60)
    
    results = {}
    
    results.update(await test_akshare())
    
    try:
        results.update(await test_pytdx())
    except Exception as e:
        print(f"Pytdx测试失败: {e}")
    
    try:
        results.update(await test_tushare())
    except Exception as e:
        print(f"Tushare测试失败: {e}")
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    # 提取指数数据测试结果
    index_times = []
    if "akshare" in results:
        index_times.append(("AKShare", results["akshare"].get("index", float('inf'))))
    if "pytdx" in results:
        index_times.append(("Pytdx", results["pytdx"].get("index", float('inf'))))
    if "tushare" in results and "error" not in results["tushare"]:
        index_times.append(("Tushare", results["tushare"].get("index", float('inf'))))
    
    index_times.sort(key=lambda x: x[1])
    
    print("\n【指数数据获取速度排名】")
    for i, (name, t) in enumerate(index_times, 1):
        if t == float('inf'):
            print(f"{i}. {name}: 失败")
        else:
            print(f"{i}. {name}: {t:.2f}秒")
    
    print("\n【功能对比】")
    print(f"{'数据源':<10} {'指数':<6} {'板块':<6} {'广度':<6} {'涨停':<6}")
    print("-"*40)
    print(f"{'AKShare':<10} {'✅':<6} {'✅':<6} {'✅':<6} {'✅':<6}")
    print(f"{'Pytdx':<10} {'✅':<6} {'❌':<6} {'❌':<6} {'❌':<6}")
    print(f"{'Tushare':<10} {'✅':<6} {'✅':<6} {'❌':<6} {'❌':<6}")
    
    print("\n【推荐配置】")
    print("- 实时行情: AKShare（功能最全）")
    print("- 低延迟需求: Pytdx（最快）")
    print("- 标准化数据: Tushare（适合回测）")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())

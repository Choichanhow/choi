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

    print("\n" + "="*60)
    print("AKShare 性能测试")
    print("="*60)

    results = {}

    # 测试指数数据
    start = time.time()
    result = await adapter.fetch_index_realtime("shanghai")
    elapsed = time.time() - start
    status = "✅ 成功" if "error" not in result else "❌ 失败"
    price = result.get("price", "N/A")
    print(f"1. 指数数据(上证): {elapsed:.2f}s [{status}] 价格:{price}")
    results["index"] = {"time": elapsed, "status": "success" if "error" not in result else "failed", "price": price}

    # 测试板块数据
    start = time.time()
    result = await adapter.fetch_sector_list()
    elapsed = time.time() - start
    count = len([r for r in result if "error" not in r])
    status = "✅ 成功" if count > 0 else "❌ 失败"
    print(f"2. 板块数据: {elapsed:.2f}s [{status}] {count}个板块")
    results["sector"] = {"time": elapsed, "status": "success", "count": count}

    # 测试涨停池
    start = time.time()
    result = await adapter.fetch_zt_pool()
    elapsed = time.time() - start
    count = len(result) if isinstance(result, list) else 0
    status = "✅ 成功" if count > 0 else "❌ 失败(可能非交易日)"
    print(f"3. 涨停池: {elapsed:.2f}s [{status}] {count}条")
    results["zt_pool"] = {"time": elapsed, "status": "success" if count > 0 else "no_data", "count": count}

    # 测试市场广度（这个比较慢）
    start = time.time()
    result = await adapter.fetch_market_breadth()
    elapsed = time.time() - start
    status = "✅ 成功" if "error" not in result else "❌ 失败"
    up_down = f"{result.get('up_count', 0)}/{result.get('down_count', 0)}" if "error" not in result else "--"
    print(f"4. 市场广度: {elapsed:.2f}s [{status}] 涨跌:{up_down}")
    results["breadth"] = {"time": elapsed, "status": "success" if "error" not in result else "failed", "breadth": up_down}

    return results


async def test_pytdx():
    from data.sources.pytdx_adapter import PytdxAdapter
    adapter = PytdxAdapter()

    print("\n" + "="*60)
    print("Pytdx 性能测试 (TCP模式)")
    print("="*60)

    results = {}

    # 健康检查
    start = time.time()
    health = await adapter.health_check()
    elapsed = time.time() - start
    status = "✅ 成功" if health else "❌ 失败"
    print(f"0. 健康检查: {elapsed:.2f}s [{status}]")
    results["health"] = {"time": elapsed, "status": "success" if health else "failed"}

    # 测试上证指数
    start = time.time()
    result = await adapter.fetch_index_realtime("shanghai")
    elapsed = time.time() - start
    status = "✅ 成功" if "error" not in result else "❌ 失败"
    price = result.get("price", "N/A")
    date_matched = result.get("date_matched", False)
    print(f"1. 指数数据(上证): {elapsed:.2f}s [{status}] 价格:{price} 日期匹配:{date_matched}")
    results["index_sh"] = {"time": elapsed, "status": "success" if "error" not in result else "failed", "price": price}

    # 测试深证指数
    start = time.time()
    result = await adapter.fetch_index_realtime("shenzhen")
    elapsed = time.time() - start
    status = "✅ 成功" if "error" not in result else "❌ 失败"
    price = result.get("price", "N/A")
    print(f"2. 指数数据(深证): {elapsed:.2f}s [{status}] 价格:{price}")
    results["index_sz"] = {"time": elapsed, "status": "success" if "error" not in result else "failed", "price": price}

    # 测试创业板
    start = time.time()
    result = await adapter.fetch_index_realtime("chinext")
    elapsed = time.time() - start
    status = "✅ 成功" if "error" not in result else "❌ 失败"
    price = result.get("price", "N/A")
    print(f"3. 指数数据(创业板): {elapsed:.2f}s [{status}] 价格:{price}")
    results["index_cy"] = {"time": elapsed, "status": "success" if "error" not in result else "failed", "price": price}

    # 测试科创50
    start = time.time()
    result = await adapter.fetch_index_realtime("star_50")
    elapsed = time.time() - start
    status = "✅ 成功" if "error" not in result else "❌ 失败"
    price = result.get("price", "N/A")
    print(f"4. 指数数据(科创50): {elapsed:.2f}s [{status}] 价格:{price}")
    results["index_star"] = {"time": elapsed, "status": "success" if "error" not in result else "failed", "price": price}

    return results


async def test_tushare():
    from data.sources.tushare_adapter import TushareAdapter
    adapter = TushareAdapter()

    print("\n" + "="*60)
    print("Tushare 性能测试")
    print("="*60)

    results = {}

    # 健康检查
    start = time.time()
    health = await adapter.health_check()
    elapsed = time.time() - start
    status = "✅ 成功" if health else "❌ 失败"
    print(f"0. 健康检查: {elapsed:.2f}s [{status}]")
    results["health"] = {"time": elapsed, "status": "success" if health else "failed"}

    if not health:
        print("Tushare: 连接失败，跳过其他测试")
        return results

    # 测试指数数据
    start = time.time()
    result = await adapter.fetch_index_realtime("shanghai")
    elapsed = time.time() - start
    status = "✅ 成功" if "error" not in result else "❌ 失败"
    price = result.get("price", "N/A")
    reason = result.get("reason", "")[:50] if "error" in result else ""
    print(f"1. 指数数据(上证): {elapsed:.2f}s [{status}] 价格:{price} {reason}")
    results["index"] = {"time": elapsed, "status": "success" if "error" not in result else "failed", "price": price}

    # 测试板块数据
    start = time.time()
    result = await adapter.fetch_sector_list()
    elapsed = time.time() - start
    count = len([r for r in result if "error" not in r]) if isinstance(result, list) else 0
    status = "✅ 成功" if count > 0 else "❌ 失败"
    print(f"2. 板块数据: {elapsed:.2f}s [{status}] {count}个板块")
    results["sector"] = {"time": elapsed, "status": "success", "count": count}

    return results


async def main():
    print("="*60)
    print("A-Share Market Dashboard 数据源性能测试报告")
    print("="*60)

    all_results = {"akshare": {}, "pytdx": {}, "tushare": {}}

    try:
        all_results["akshare"] = await test_akshare()
    except Exception as e:
        print(f"AKShare测试失败: {e}")

    try:
        all_results["pytdx"] = await test_pytdx()
    except Exception as e:
        print(f"Pytdx测试失败: {e}")

    try:
        all_results["tushare"] = await test_tushare()
    except Exception as e:
        print(f"Tushare测试失败: {e}")

    print("\n" + "="*60)
    print("性能测试结果汇总")
    print("="*60)

    # 指数速度排名
    print("\n【指数数据获取速度排名】")
    index_times = []
    if "index" in all_results["akshare"]:
        t = all_results["akshare"]["index"]["time"]
        index_times.append(("AKShare", t, all_results["akshare"]["index"].get("price", "N/A")))
    if "index_sh" in all_results["pytdx"]:
        t = all_results["pytdx"]["index_sh"]["time"]
        index_times.append(("Pytdx", t, all_results["pytdx"]["index_sh"].get("price", "N/A")))
    if "index" in all_results["tushare"] and all_results["tushare"]["index"].get("status") == "success":
        t = all_results["tushare"]["index"]["time"]
        index_times.append(("Tushare", t, all_results["tushare"]["index"].get("price", "N/A")))

    index_times.sort(key=lambda x: x[1])
    for i, (name, t, price) in enumerate(index_times, 1):
        print(f"  {i}. {name}: {t:.2f}秒 (价格:{price})")

    # 功能对比
    print("\n【功能对比】")
    print(f"  {'数据源':<10} {'指数':<8} {'板块':<8} {'广度':<8} {'涨停':<8}")
    print(f"  {'-'*50}")
    akshare_ok = "✅" if "index" in all_results["akshare"] else "❌"
    pytdx_ok = "✅" if "index_sh" in all_results["pytdx"] else "❌"
    tushare_ok = "✅" if "index" in all_results["tushare"] and all_results["tushare"]["index"].get("status") == "success" else "❌"

    akshare_sector = "✅" if all_results["akshare"].get("sector", {}).get("count", 0) > 0 else "❌"
    tushare_sector = "✅" if all_results["tushare"].get("sector", {}).get("count", 0) > 0 else "❌"

    akshare_breadth = "✅" if all_results["akshare"].get("breadth", {}).get("status") == "success" else "❌"
    akshare_zt = "✅" if all_results["akshare"].get("zt_pool", {}).get("status") == "success" else "❌"

    print(f"  {'AKShare':<10} {akshare_ok:<8} {akshare_sector:<8} {akshare_breadth:<8} {akshare_zt:<8}")
    print(f"  {'Pytdx':<10} {pytdx_ok:<8} {'❌':<8} {'❌':<8} {'❌':<8}")
    print(f"  {'Tushare':<10} {tushare_ok:<8} {tushare_sector:<8} {'❌':<8} {'❌':<8}")

    # 数据准确性
    print("\n【数据准确性验证】")
    ak_price = all_results["akshare"].get("index", {}).get("price", 0)
    tdx_price = all_results["pytdx"].get("index_sh", {}).get("price", 0)
    if ak_price and tdx_price:
        diff = abs(ak_price - tdx_price)
        diff_pct = diff / ak_price * 100 if ak_price else 0
        print(f"  AKShare 上证: {ak_price}")
        print(f"  Pytdx 上证: {tdx_price}")
        print(f"  差异: {diff:.2f} ({diff_pct:.2f}%)")
        if diff_pct < 1:
            print(f"  结论: ✅ 数据基本一致")
        else:
            print(f"  结论: ⚠️ 数据差异较大，请检查")

    # 推荐配置
    print("\n【推荐配置】")
    print("  • 实时行情首选: AKShare（功能最全，数据准确）")
    print("  • 低延迟需求: Pytdx（速度最快，但需注意数据日期验证）")
    print("  • 标准化数据/回测: Tushare（数据规范，但部分接口需高级权限）")

    # 保存结果
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print("\n详细结果已保存到 test_results.json")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())

"""
Pytdx 最优服务器自动选择 + 性能基准测试
"""

import socket
import time
import sys

sys.path.insert(0, "h:\\QUART")

from pytdx.hq import TdxHq_API
from pytdx.config.hosts import hq_hosts


def test_tcp_connect(host, port, timeout=3):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        start = time.time()
        s.connect((host, port))
        elapsed = round((time.time() - start) * 1000)
        s.close()
        return True, elapsed
    except Exception:
        return False, -1


def benchmark_server(name, host, port, attempts=3):
    times = []
    for _ in range(attempts):
        try:
            api = TdxHq_API(heartbeat=False)
            api.connect(ip=host, port=port, time_out=5)
            start = time.time()
            data = api.get_security_quotes([(0, "000001"), (0, "399001"), (0, "399006")])
            elapsed = round((time.time() - start) * 1000)
            api.disconnect()
            if data:
                times.append(elapsed)
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass
            return None
    return times


def main():
    print("=" * 60)
    print("第一步: TCP 连通性筛选")
    print("=" * 60)

    reachable = []
    for entry in hq_hosts:
        name, host, port = entry[0], entry[1], entry[2]
        ok, tcp_ms = test_tcp_connect(host, port)
        if ok:
            reachable.append((name, host, port))

    print(f"可达服务器: {len(reachable)}/{len(hq_hosts)}")

    if not reachable:
        print("无可用服务器，终止")
        return

    print("\n" + "=" * 60)
    print("第二步: Pytdx API 延迟基准测试 (3次取平均)")
    print("=" * 60)

    results = []
    for name, host, port in reachable:
        times = benchmark_server(name, host, port, attempts=3)
        if times:
            avg = round(sum(times) / len(times), 1)
            min_t = min(times)
            max_t = max(times)
            results.append((avg, min_t, max_t, name, host, port))
            print(f"  ✅ {name}: avg={avg}ms  min={min_t}ms  max={max_t}ms  ({host}:{port})")
        else:
            print(f"  ❌ {name}: API调用失败  ({host}:{port})")

    if not results:
        print("所有服务器API调用均失败")
        return

    results.sort(key=lambda x: x[0])
    best = results[0]

    print("\n" + "=" * 60)
    print("最优服务器")
    print("=" * 60)
    print(f"  名称: {best[3]}")
    print(f"  地址: {best[4]}:{best[5]}")
    print(f"  平均延迟: {best[0]}ms")

    print("\n" + "=" * 60)
    print("Top 5 服务器排名")
    print("=" * 60)
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r[3]}  avg={r[0]}ms  min={r[1]}ms  max={r[2]}ms  {r[4]}:{r[5]}")

    print("\n" + "=" * 60)
    print("保存最优服务器到配置")
    print("=" * 60)
    print(f"BEST_IP = ('{best[4]}', {best[5]})  # {best[3]}")


if __name__ == "__main__":
    main()

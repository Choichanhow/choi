"""
指数数据对比测试 - AKShare vs Pytdx
"""
import asyncio
from data.sources.akshare_adapter import AKShareAdapter
from data.sources.pytdx_adapter import PytdxAdapter


async def test():
    akshare = AKShareAdapter()
    pytdx = PytdxAdapter()

    indices = ['shanghai', 'shenzhen', 'chinext', 'star_50', 'star_composite', 'csi_all']

    print('=' * 70)
    print(f"{'指数':<15} {'AKShare价格':>12} {'Pytdx价格':>12} {'差异':>10}")
    print('=' * 70)

    for idx in indices:
        ak_result = await akshare.fetch_index_realtime(idx)
        tdx_result = await pytdx.fetch_index_realtime(idx)

        ak_price = ak_result.get('price', 0)
        tdx_price = tdx_result.get('price', 0)
        diff = abs(ak_price - tdx_price) if ak_price and tdx_price else 0
        diff_pct = diff / ak_price * 100 if ak_price else 0

        status = '✅' if diff_pct < 0.1 else '⚠️'
        print(f"{idx:<15} {ak_price:>12.2f} {tdx_price:>12.2f} {diff_pct:>9.2f}% {status}")

    print('=' * 70)


if __name__ == "__main__":
    asyncio.run(test())

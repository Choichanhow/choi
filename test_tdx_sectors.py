import asyncio
from data.sources.pytdx_adapter import PytdxAdapter
from config.tdx_industry import get_tdx_industry_list

async def test():
    adapter = PytdxAdapter()
    
    print('Testing TDX industry sectors...')
    result = await adapter.fetch_industry_sectors()
    
    if result and len(result) > 0:
        print('Success! Found', len(result), 'sectors')
        print()
        print('Top 5 sectors:')
        for s in result[:5]:
            print('  {} ({}): price={}, change={}%, amount={}'.format(
                s['sector_name'], s['sector_code'], s['price'], s['change_pct'], s.get('amount')
            ))
    else:
        print('Failed or empty result')
        print(result)

asyncio.run(test())

import asyncio
from data.sources.akshare_adapter import AKShareAdapter

async def test():
    adapter = AKShareAdapter()
    print('Fetching sector data...')
    result = await adapter.fetch_sector_list()
    if result and len(result) > 0:
        print('Sample sector:', result[0])
        print()
        print('First 3 sectors:')
        for s in result[:3]:
            print('  {}: change={}%, amount={}'.format(s['sector_name'], s['change_pct'], s.get('amount', 'N/A')))
    else:
        print('No data')

asyncio.run(test())

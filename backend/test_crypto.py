import asyncio
from datetime import date, timedelta
from stock_agent.storage.repository import storage_layer
from stock_agent.collectors.price_collector import PriceCollector

async def main():
    pc = PriceCollector(storage_layer)
    end = date.today()
    start = end - timedelta(days=500) # test with ~1.5 years
    bars = await pc.collect_historical_bars("BTC", start, end)
    print(f"Collected {len(bars)} BTC bars. Last bar: {bars[-1].timestamp if bars else None}")

asyncio.run(main())

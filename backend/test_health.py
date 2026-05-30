import asyncio
from stock_agent.storage.integrity_checker import integrity_checker

async def main():
    res = await integrity_checker.check_universe_data_health()
    print("Deficient Tickers:", res["deficient_tickers"])
    print("Count:", res["deficient_count"])

asyncio.run(main())

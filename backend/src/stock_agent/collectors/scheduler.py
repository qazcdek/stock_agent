from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from stock_agent.core.config import settings
from stock_agent.collectors.price_collector import PriceCollector
from stock_agent.collectors.news_collector import NewsCollector
from stock_agent.core.interfaces import DataRepository
from stock_agent.monitoring.logger import logger
from stock_agent.common.calendar import Market, trading_calendar
import pytz

def get_market_for_ticker(ticker: str) -> Market:
    if ticker.isdigit():
        return Market.KOSPI
    elif "BTC" in ticker or "ETH" in ticker or "USDT" in ticker:
        return Market.CRYPTO
    else:
        return Market.US

class CollectionScheduler:
    def __init__(self, repository: DataRepository):
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Seoul'))
        self.price_collector = PriceCollector(repository)
        self.news_collector = NewsCollector()
        self.repository = repository

    def start(self) -> None:
        """Starts the scheduler daemon."""
        logger.info("Starting background collection scheduler...")
        
        # Tier 1 - KOSPI: 15:30 KST every weekday
        self.scheduler.add_job(
            self._collect_prices_for_market,
            args=[Market.KOSPI],
            trigger=CronTrigger(day_of_week="mon-fri", hour=15, minute=30, timezone='Asia/Seoul'),
            id="price_collection_kospi",
            name="Daily Price Data Collection - KOSPI",
            replace_existing=True
        )

        # Tier 1 - US: 06:30 KST every Tue-Sat (which corresponds to US Mon-Fri close)
        self.scheduler.add_job(
            self._collect_prices_for_market,
            args=[Market.US],
            trigger=CronTrigger(day_of_week="tue-sat", hour=6, minute=30, timezone='Asia/Seoul'),
            id="price_collection_us",
            name="Daily Price Data Collection - US",
            replace_existing=True
        )

        # Tier 1 - CRYPTO: 09:00 KST every day (UTC 00:00)
        self.scheduler.add_job(
            self._collect_prices_for_market,
            args=[Market.CRYPTO],
            trigger=CronTrigger(hour=9, minute=0, timezone='Asia/Seoul'),
            id="price_collection_crypto",
            name="Daily Price Data Collection - CRYPTO",
            replace_existing=True
        )

        # Schedule news & disclosure sentiment parsing every hour
        self.scheduler.add_job(
            self._collect_all_news,
            trigger=CronTrigger(minute=0),
            id="news_collection_job",
            name="Hourly News & Disclosure Sentiment Collection",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Collection scheduler started.")

    def shutdown(self) -> None:
        """Gracefully shuts down the scheduler."""
        logger.info("Shutting down collection scheduler...")
        self.scheduler.shutdown()

    async def trigger_immediate_collection(self) -> None:
        """Triggers all collection jobs immediately for manual syncing or initial seeding."""
        logger.info("Triggering immediate manual data collection cycle...")
        await self._collect_prices_for_market(Market.KOSPI)
        await self._collect_prices_for_market(Market.US)
        await self._collect_prices_for_market(Market.CRYPTO)
        await self._collect_all_news()

    async def _collect_prices_for_market(self, target_market: Market) -> None:
        logger.info(f"Executing periodic price collection job for {target_market.value}")
        from stock_agent.storage.repository import get_trading_universe
        for ticker in get_trading_universe():
            if get_market_for_ticker(ticker) != target_market:
                continue
            try:
                await self.price_collector.collect_daily_close(ticker)
            except Exception as e:
                logger.error("Failed to run scheduled price collection", ticker=ticker, market=target_market.value, error=str(e))

    async def _collect_all_news(self) -> None:
        logger.info("Executing periodic news and disclosure collection job")
        try:
            await self.news_collector.collect_general_news()
        except Exception as e:
            logger.error("Failed to run scheduled general news collection", error=str(e))

        from stock_agent.storage.repository import get_trading_universe
        for ticker in get_trading_universe():
            try:
                await self.news_collector.collect_naver_news(ticker)
                await self.news_collector.collect_dart_disclosures(ticker)
            except Exception as e:
                logger.error("Failed to run scheduled news collection", ticker=ticker, error=str(e))

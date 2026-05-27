from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from stock_agent.core.config import settings
from stock_agent.collectors.price_collector import PriceCollector
from stock_agent.collectors.news_collector import NewsCollector
from stock_agent.core.interfaces import DataRepository
from stock_agent.monitoring.logger import logger

class CollectionScheduler:
    def __init__(self, repository: DataRepository):
        self.scheduler = AsyncIOScheduler()
        self.price_collector = PriceCollector(repository)
        self.news_collector = NewsCollector()
        self.repository = repository

    def start(self) -> None:
        """Starts the scheduler daemon."""
        logger.info("Starting background collection scheduler...")
        
        # Schedule price OHLCV data collection at 15:45 KST every weekday (Monday-Friday)
        # Note: KST timezone or standard system local time
        self.scheduler.add_job(
            self._collect_all_prices,
            trigger=CronTrigger(day_of_week="mon-fri", hour=15, minute=45),
            id="price_collection_job",
            name="Daily Price Data Collection at Market Close",
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
        await self._collect_all_prices()
        await self._collect_all_news()

    async def _collect_all_prices(self) -> None:
        logger.info("Executing periodic price collection job for active universe")
        for ticker in settings.TRADING_UNIVERSE:
            try:
                await self.price_collector.collect_daily_close(ticker)
            except Exception as e:
                logger.error("Failed to run scheduled price collection", ticker=ticker, error=str(e))

    async def _collect_all_news(self) -> None:
        logger.info("Executing periodic news and disclosure collection job")
        for ticker in settings.TRADING_UNIVERSE:
            try:
                await self.news_collector.collect_naver_news(ticker)
                await self.news_collector.collect_dart_disclosures(ticker)
            except Exception as e:
                logger.error("Failed to run scheduled news collection", ticker=ticker, error=str(e))

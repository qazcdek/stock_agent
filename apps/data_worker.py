import asyncio
import signal
from stock_agent.infra.storage.sqlite_repo import SQLiteRepository
from stock_agent.collectors.scheduler import CollectionScheduler
from stock_agent.monitoring.logger import logger

class DataWorker:
    def __init__(self):
        self.repository = SQLiteRepository()
        self.scheduler = CollectionScheduler(self.repository)
        self.running = True

    def stop(self, *args):
        logger.info("Termination signal received. Shutting down worker...")
        self.running = False
        self.scheduler.shutdown()

    async def run(self):
        # Register OS signal handlers for graceful exit
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:
                # Fallback for Windows which does not support add_signal_handler fully
                pass

        logger.info("Initializing DataWorker daemon...")
        
        # Trigger an immediate manual collection on startup to ensure we have initial data
        await self.scheduler.trigger_immediate_collection()
        
        # Start background APScheduler
        self.scheduler.start()
        
        logger.info("DataWorker is actively listening. Press Ctrl+C to exit.")
        while self.running:
            await asyncio.sleep(1)

if __name__ == "__main__":
    worker = DataWorker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("DataWorker stopped manually.")

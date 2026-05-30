import asyncio
import argparse
import signal
from stock_agent.core.config import settings
from stock_agent.infra.storage.sqlite_repo import SQLiteRepository
from stock_agent.infra.brokers.paper_broker import PaperBroker
from stock_agent.infra.brokers.kis_broker import KISBroker
from stock_agent.infra.llm.provider import DeepLLMProxy
from stock_agent.execution.trader import StockTrader
from stock_agent.monitoring.notifier import notifier
from stock_agent.monitoring.logger import logger

class TraderWorker:
    def __init__(self, mode: str, interval_sec: int):
        self.interval_sec = interval_sec
        self.repository = SQLiteRepository()
        self.llm_client = DeepLLMProxy()
        
        # Configure Broker target based on argument
        if mode.lower() == "kis":
            logger.info("Initializing TraderWorker in KIS Broker Mode (한국투자증권 API)")
            self.broker = KISBroker()
        else:
            logger.info("Initializing TraderWorker in virtual simulated Paper Broker Mode")
            self.broker = PaperBroker()

        self.trader = StockTrader(self.broker, self.repository, self.llm_client)
        self.running = True

    def stop(self, *args):
        logger.info("Termination signal received. Stopping live trader worker...")
        self.running = False

    async def run(self):
        # Handle OS process exit signals
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:
                # Bypass on platforms that lack support
                pass

        from stock_agent.storage.repository import get_trading_universe
        logger.info("TraderWorker started.", interval=self.interval_sec, universe=get_trading_universe())
        await notifier.notify("🚀 <b>주식 자동 매매 에이전트 워커가 가동되었습니다.</b>")

        # Main active trading loop
        while self.running:
            # Check market hours (Korean Stock Market: 09:00 - 15:30 KST)
            # In development/paper mode, we bypass market hour restrictions for testing ease
            logger.info("Starting periodic trading cycle tick...")
            await self.trader.execute_trade_cycle()
            
            logger.info("Cycle completed. Going to sleep...", sleep_seconds=self.interval_sec)
            
            # Non-blocking sleep cycle checking running status every second
            for _ in range(self.interval_sec):
                if not self.running:
                    break
                await asyncio.sleep(1)

        await notifier.notify("🛑 <b>주식 자동 매매 에이전트 워커가 정상 종료되었습니다.</b>")
        logger.info("TraderWorker successfully terminated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live automated stock trading daemon worker")
    parser.add_argument("--mode", type=str, default="paper", choices=["paper", "kis"], help="Broker target (paper: virtual mock, kis: Korea Investment API)")
    parser.add_argument("--interval", type=int, default=60, help="Trading loop cycle execution interval in seconds")
    
    args = parser.parse_args()

    worker = TraderWorker(mode=args.mode, interval_sec=args.interval)
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("TraderWorker stopped manually.")

import asyncio
import json
from datetime import datetime
import uvicorn
from stock_agent.common.logger import logger
from stock_agent.collectors.data_collector import DataCollector
from stock_agent.web.server import app

# Import all modules to trigger event subscriptions inside EventBus!
import stock_agent.preprocessor
import stock_agent.ml_system
import stock_agent.agent_system
import stock_agent.strategy_engine
import stock_agent.risk_manager
import stock_agent.approval_queue
import stock_agent.oms
import stock_agent.exchange_adapter
import stock_agent.portfolio_manager
import stock_agent.notification


async def run_data_tick_generator():
    """Background loop that simulates real-time stock/crypto ticks every 10 seconds."""
    from stock_agent.core.config import settings
    collector = DataCollector()
    
    logger.info("Starting background real-time mock exchange data pipeline...")
    await asyncio.sleep(2) # brief delay to let uvicorn web server spin up fully
    
    while True:
        try:
            current_time = datetime.now()
            # Feed ticks into the pipeline dynamically from SQLite DB Watchlist table
            from stock_agent.storage.repository import get_trading_universe
            tickers = get_trading_universe()
            # Ensure at least our default fallback list is present if empty
            if not tickers:
                tickers = ["005930", "035720", "BTC"]
                
            for t in tickers:
                await collector.collect_data(t, current_time)
                # tiny sleep to space out tickers slightly
                await asyncio.sleep(0.5)
                
            logger.info("Real-time pricing loop completed a tick set", active_universe=tickers)
        except Exception as e:
            logger.error("Error in real-time pricing thread loop", error=str(e))
            
        await asyncio.sleep(8.0) # tick set every 10 seconds


async def main():
    # Start the data simulation loop as an asyncio background task
    asyncio.create_task(run_data_tick_generator())
    
    # Run uvicorn web server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System shut down gracefully.")

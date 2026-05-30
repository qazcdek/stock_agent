import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from stock_agent.common.logger import logger
from stock_agent.collectors.price_collector import PriceCollector
from stock_agent.storage.repository import storage_layer

class DataSeeder:
    """Background worker to seed 10 years of historical data for deficient tickers."""
    
    def __init__(self):
        self.price_collector = PriceCollector(storage_layer)
        self.is_running = False
        self.progress = {"status": "idle", "total": 0, "completed": 0, "current_ticker": None}
        
    async def run_bulk_seed(self, deficient_tickers: List[Dict[str, Any]]):
        """Runs the bulk seeding operation carefully with rate limiting delays."""
        if self.is_running:
            logger.warning("DataSeeder is already running. Ignoring new trigger.")
            return
            
        self.is_running = True
        self.progress["status"] = "running"
        self.progress["total"] = len(deficient_tickers)
        self.progress["completed"] = 0
        
        logger.info("Starting DataSeeder bulk update...", count=len(deficient_tickers))
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=3650) # Approx 10 years
        
        try:
            for item in deficient_tickers:
                ticker = item["ticker"]
                self.progress["current_ticker"] = ticker
                logger.info(f"Seeding historical data for {ticker} ({start_date} to {end_date})")
                
                try:
                    await self.price_collector.collect_historical_bars(ticker, start_date, end_date)
                    self._mark_seeded(ticker)
                except Exception as e:
                    logger.error(f"Failed to seed data for {ticker}", error=str(e))
                
                self.progress["completed"] += 1
                # Sleep to avoid hitting API rate limits aggressively
                await asyncio.sleep(1.0)
                
            self.progress["status"] = "completed"
            logger.info("DataSeeder bulk update completed successfully.")
        except Exception as e:
            self.progress["status"] = "failed"
            logger.error("DataSeeder bulk update failed unexpectedly", error=str(e))
        finally:
            self.is_running = False
            self.progress["current_ticker"] = None

    def _mark_seeded(self, ticker: str):
        import json
        import os
        seeded_file = storage_layer.db_path + ".seeded.json"
        seeded = set()
        if os.path.exists(seeded_file):
            try:
                with open(seeded_file, "r") as f:
                    seeded = set(json.load(f))
            except Exception:
                pass
        seeded.add(ticker)
        with open(seeded_file, "w") as f:
            json.dump(list(seeded), f)

data_seeder = DataSeeder()

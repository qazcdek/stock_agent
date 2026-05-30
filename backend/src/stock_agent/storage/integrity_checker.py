import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from stock_agent.common.logger import logger
from stock_agent.infra.storage.multi_db import clickhouse_manager, duckdb_manager, postgres_manager
from stock_agent.storage.universe_manager import universe_manager

class DataIntegrityChecker:
    """Checks the health and completeness of data for the target universe."""
    
    def __init__(self):
        pass
        
    async def check_universe_data_health(self) -> Dict[str, Any]:
        """Runs integrity checks and returns missing/deficient tickers."""
        universe = await universe_manager.get_target_universe()
        
        # Determine current date/time to check recency
        now = datetime.now()
        three_biz_days_ago = now - timedelta(days=5) # 5 days roughly covers weekends
        
        deficient_tickers = []
        
        # We can run a group by query to get counts and max dates for all tickers at once
        # using the clickhouse_manager if active, else fallback to storage_layer SQLite
        
        stats = await self._get_db_stats()
        
        for ticker in universe:
            ticker_stat = stats.get(ticker)
            if not ticker_stat:
                # No data at all
                deficient_tickers.append({"ticker": ticker, "reason": "no_data"})
                continue
                
            count = ticker_stat["count"]
            max_date = ticker_stat["max_date"]
            
            # Check if seeded
            is_seeded = False
            try:
                import os, json
                from stock_agent.storage.repository import storage_layer
                seeded_file = storage_layer.db_path + ".seeded.json"
                if os.path.exists(seeded_file):
                    with open(seeded_file, "r") as f:
                        if ticker in set(json.load(f)):
                            is_seeded = True
            except Exception:
                pass

            # Deficiency Criteria:
            # 1. Less than 1000 bars AND not marked as seeded
            # 2. Latest bar is older than 5 days ago (stale)
            if count < 1000 and not is_seeded:
                deficient_tickers.append({"ticker": ticker, "reason": f"insufficient_history: {count} bars"})
            elif max_date < three_biz_days_ago:
                deficient_tickers.append({"ticker": ticker, "reason": f"stale_data: latest is {max_date.date()}"})
                
        requires_bulk_update = len(deficient_tickers) > 0
        
        return {
            "requires_bulk_update": requires_bulk_update,
            "deficient_tickers": deficient_tickers,
            "total_universe_size": len(universe),
            "deficient_count": len(deficient_tickers),
            "checked_at": now.isoformat()
        }
        
    async def _get_db_stats(self) -> Dict[str, Dict[str, Any]]:
        """Returns { 'AAPL': {'count': 2500, 'max_date': datetime(...) } }"""
        stats = {}
        if clickhouse_manager.active and clickhouse_manager.client is not None:
            try:
                res = clickhouse_manager.client.query("SELECT ticker, COUNT(*), MAX(timestamp) FROM bars GROUP BY ticker")
                for row in res.result_rows:
                    stats[row[0]] = {"count": row[1], "max_date": row[2]}
                return stats
            except Exception as e:
                logger.error("DataIntegrityChecker failed ClickHouse check", error=str(e))
                
        # Fallback to SQLite
        try:
            from stock_agent.storage.repository import storage_layer
            conn = storage_layer._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker, COUNT(*), MAX(timestamp) FROM ts_bars GROUP BY ticker")
            for row in cursor.fetchall():
                max_d = datetime.fromisoformat(row[2]) if row[2] else datetime.min
                stats[row[0]] = {"count": row[1], "max_date": max_d}
            conn.close()
        except Exception as e:
            logger.error("DataIntegrityChecker failed SQLite check", error=str(e))
            
        return stats

integrity_checker = DataIntegrityChecker()

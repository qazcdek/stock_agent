import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict
import FinanceDataReader as fdr
from stock_agent.common.logger import logger

# Crypto 30: Top 30 by market cap (May 2026 snapshot) - filtered for Coinone KRW pairs
CRYPTO_30 = [
    "BTC", "ETH", "USDT", "BNB", "XRP", "USDC", "SOL", "TRX", "DOGE", "ADA", 
    "XLM", "LINK", "BCH", "TON", "USD1", "HBAR", "AVAX", "SUI", "NEAR", "SHIB"
]

class UniverseManager:
    """Manages the target universe (KOSPI 100, S&P 500, Crypto 30).
    Caches the list locally and only updates if the year changes (Jan 1st snapshot).
    """
    
    def __init__(self, cache_dir: str = "data/universe"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
    async def get_target_universe(self) -> List[str]:
        """Returns the full list of tickers across all three target markets."""
        kospi_100 = await self.get_kospi_100()
        sp_500 = await self.get_sp_500()
        return kospi_100 + sp_500 + CRYPTO_30
        
    async def get_kospi_100(self) -> List[str]:
        return await self._get_cached_or_fetch("kospi_100", self._fetch_kospi_100)
        
    async def get_sp_500(self) -> List[str]:
        return await self._get_cached_or_fetch("sp_500", self._fetch_sp_500)
        
    async def get_crypto_30(self) -> List[str]:
        return CRYPTO_30
        
    async def _get_cached_or_fetch(self, name: str, fetch_func) -> List[str]:
        current_year = datetime.now().year
        cache_file = os.path.join(self.cache_dir, f"{name}_{current_year}.json")
        
        # Check if cache exists for the current year
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("tickers", [])
            except Exception as e:
                logger.warning(f"Failed to read universe cache for {name}", error=str(e))
                
        # Fetch fresh data
        try:
            logger.info(f"Fetching fresh universe list for {name} for year {current_year}...")
            tickers = await fetch_func()
            if tickers:
                # Save cache
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"year": current_year, "tickers": tickers}, f, indent=2)
                return tickers
        except Exception as e:
            logger.error(f"Failed to fetch universe for {name}", error=str(e))
            
        # Fallback to older caches if fresh fetch fails
        return self._get_latest_fallback_cache(name)

    async def _fetch_kospi_100(self) -> List[str]:
        # KOSPI 100 based on Market Cap
        def _fetch():
            df = fdr.StockListing("KOSPI")
            if "Marcap" in df.columns:
                df = df.sort_values("Marcap", ascending=False).head(100)
                return df["Code"].tolist()
            else:
                return df["Code"].head(100).tolist()
        return await asyncio.to_thread(_fetch)
        
    async def _fetch_sp_500(self) -> List[str]:
        # S&P 500 components
        def _fetch():
            df = fdr.StockListing("S&P500")
            return df["Symbol"].tolist()
        return await asyncio.to_thread(_fetch)
        
    def _get_latest_fallback_cache(self, name: str) -> List[str]:
        import glob
        pattern = os.path.join(self.cache_dir, f"{name}_*.json")
        files = glob.glob(pattern)
        if not files:
            return []
        
        files.sort(reverse=True)
        try:
            with open(files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tickers", [])
        except:
            return []

universe_manager = UniverseManager()

import random
import httpx
import asyncio
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import FinanceDataReader as fdr

from stock_agent.core.config import settings
from stock_agent.common.dto import Bar, RawDataCollectedEvent
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.storage.repository import storage_layer
from stock_agent.infra.storage.multi_db import clickhouse_manager


class DataCollector:
    def __init__(self, tickers: List[str] = ["005930", "035720", "BTC"]):
        self.tickers = tickers
        self._cache: Dict[str, Bar] = {}
        self._last_fetch_time: Dict[str, datetime] = {}
        self.ttl_seconds = 300  # 5-minute cache TTL
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY

    async def _fetch_from_finance_datareader(self, ticker: str, start_date: date, end_date: date) -> List[Bar]:
        """Wrapper to call FinanceDataReader.DataReader asynchronously in an executor thread."""
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        logger.debug("Calling FinanceDataReader in DataCollector", ticker=ticker, start=start_str, end=end_str)
        
        # FDR is synchronous, run in thread pool
        df = await asyncio.to_thread(fdr.DataReader, ticker, start_str, end_str)
        
        if df is None or df.empty:
            return []

        bars = []
        for timestamp, row in df.iterrows():
            open_val = float(row.get("Open", row.get("open", 0.0)))
            high_val = float(row.get("High", row.get("high", 0.0)))
            low_val = float(row.get("Low", row.get("low", 0.0)))
            close_val = float(row.get("Close", row.get("close", 0.0)))
            vol_val = float(row.get("Volume", row.get("volume", 0.0)))

            if open_val <= 0.0 or close_val <= 0.0:
                continue

            bars.append(
                Bar(
                    ticker=ticker,
                    timestamp=timestamp.to_pydatetime() if hasattr(timestamp, 'to_pydatetime') else timestamp,
                    open=open_val,
                    high=high_val,
                    low=low_val,
                    close=close_val,
                    volume=vol_val
                )
            )
        return bars

    async def _fetch_from_alpha_vantage(self, ticker: str, start_date: date, end_date: date) -> List[Bar]:
        """Queries the Alpha Vantage TIME_SERIES_DAILY endpoint asynchronously."""
        av_symbol = ticker
        if ticker.isdigit():
            av_symbol = f"{ticker}.KS"

        logger.debug("Requesting Alpha Vantage in DataCollector", symbol=av_symbol)
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": av_symbol,
            "outputsize": "full",
            "apikey": self.alpha_vantage_key
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15.0)
            if response.status_code != 200:
                raise RuntimeError(f"Alpha Vantage HTTP error: {response.status_code}")
                
            data = response.json()
            time_series = data.get("Time Series (Daily)")
            
            if not time_series:
                note = data.get("Note") or data.get("Error Message")
                raise RuntimeError(f"Alpha Vantage API error: {note}")

            bars = []
            for date_str, metrics in time_series.items():
                bar_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if start_date <= bar_date <= end_date:
                    bars.append(
                        Bar(
                            ticker=ticker,
                            timestamp=datetime.combine(bar_date, datetime.min.time()),
                            open=float(metrics["1. open"]),
                            high=float(metrics["2. high"]),
                            low=float(metrics["3. low"]),
                            close=float(metrics["4. close"]),
                            volume=float(metrics["5. volume"])
                        )
                    )
            # Return sorted ascending by date
            bars.sort(key=lambda x: x.timestamp)
            return bars

    def generate_next_bar(self, ticker: str, timestamp: datetime) -> Bar:
        """Deterministic offline fallback bar generator to prevent crashes if APIs fail."""
        random.seed(hash(ticker) % 12345)
        base_price = 70000.0 if ticker == "005930" else (180000.0 if ticker == "000660" else 190000.0)
        
        change = base_price * random.uniform(-0.015, 0.02)
        o_price = base_price
        c_price = base_price + change
        h_price = max(o_price, c_price) + (base_price * random.uniform(0.001, 0.005))
        l_price = min(o_price, c_price) - (base_price * random.uniform(0.001, 0.005))
        
        return Bar(
            ticker=ticker,
            timestamp=timestamp,
            open=round(o_price, 2),
            high=round(h_price, 2),
            low=round(l_price, 2),
            close=round(c_price, 2),
            volume=float(random.randint(500000, 2000000))
        )

    async def collect_data(self, ticker: str, timestamp: datetime) -> Bar:
        """Fetch, cache, and publish real raw market data bar from FinanceDataReader or Alpha Vantage."""
        now = datetime.now()
        
        # 1. Return from cache if within TTL
        if ticker in self._cache and ticker in self._last_fetch_time:
            if (now - self._last_fetch_time[ticker]).total_seconds() < self.ttl_seconds:
                cached_bar = self._cache[ticker]
                
                updated_bar = Bar(
                    ticker=cached_bar.ticker,
                    timestamp=timestamp,
                    open=cached_bar.open,
                    high=cached_bar.high,
                    low=cached_bar.low,
                    close=cached_bar.close,
                    volume=cached_bar.volume
                )
                
                # Save to DB with midnight timestamp to maintain exactly 1 bar per day
                db_bar = Bar(
                    ticker=cached_bar.ticker,
                    timestamp=datetime.combine(timestamp.date(), datetime.min.time()),
                    open=cached_bar.open,
                    high=cached_bar.high,
                    low=cached_bar.low,
                    close=cached_bar.close,
                    volume=cached_bar.volume
                )
                await clickhouse_manager.save_bar(db_bar)
                
                await event_bus.publish(RawDataCollectedEvent(ticker=ticker, bar=updated_bar))
                logger.debug("Raw data served from DataCollector cache", ticker=ticker, close=updated_bar.close)
                return updated_bar

        # 2. Fetch real data (lookback 60 days to populate chart history properly)
        bars = []
        start_date = (now - timedelta(days=60)).date()
        end_date = now.date()

        # Tier 1: FinanceDataReader
        try:
            bars = await self._fetch_from_finance_datareader(ticker, start_date, end_date)
        except Exception as e:
            logger.warning("FinanceDataReader failed in DataCollector, falling back to Alpha Vantage", ticker=ticker, error=str(e))

        # Tier 2: Alpha Vantage
        if not bars and self.alpha_vantage_key and self.alpha_vantage_key != "your_alpha_vantage_api_key_here":
            try:
                bars = await self._fetch_from_alpha_vantage(ticker, start_date, end_date)
            except Exception as e:
                logger.warning("Alpha Vantage failed in DataCollector", ticker=ticker, error=str(e))

        if bars:
            bars.sort(key=lambda x: x.timestamp)
            
            # Save ALL historical bars to ensure the database has full chart data
            for bar in bars:
                bar_copy = Bar(
                    ticker=bar.ticker,
                    timestamp=datetime.combine(bar.timestamp.date(), datetime.min.time()),
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume
                )
                await clickhouse_manager.save_bar(bar_copy)
                
            latest_bar = bars[-1]
            
            # Cache it
            self._cache[ticker] = latest_bar
            self._last_fetch_time[ticker] = now
            
            # Publish event with rolling timestamp
            updated_bar = Bar(
                ticker=latest_bar.ticker,
                timestamp=timestamp,
                open=latest_bar.open,
                high=latest_bar.high,
                low=latest_bar.low,
                close=latest_bar.close,
                volume=latest_bar.volume
            )
            await event_bus.publish(RawDataCollectedEvent(ticker=ticker, bar=updated_bar))
            logger.info("Raw data successfully fetched from real API and published", ticker=ticker, close=updated_bar.close)
            return updated_bar

        # 3. Fallback to expired cache or deterministic mock values if completely offline
        if ticker in self._cache:
            cached_bar = self._cache[ticker]
            updated_bar = Bar(
                ticker=cached_bar.ticker,
                timestamp=timestamp,
                open=cached_bar.open,
                high=cached_bar.high,
                low=cached_bar.low,
                close=cached_bar.close,
                volume=cached_bar.volume
            )
            db_bar = Bar(
                ticker=cached_bar.ticker,
                timestamp=datetime.combine(timestamp.date(), datetime.min.time()),
                open=cached_bar.open,
                high=cached_bar.high,
                low=cached_bar.low,
                close=cached_bar.close,
                volume=cached_bar.volume
            )
            await clickhouse_manager.save_bar(db_bar)
            await event_bus.publish(RawDataCollectedEvent(ticker=ticker, bar=updated_bar))
            logger.warning("Using expired cache fallback in DataCollector due to API failure", ticker=ticker)
            return updated_bar

        # Offline deterministic fallback
        fallback_bar = self.generate_next_bar(ticker, timestamp)
        self._cache[ticker] = fallback_bar
        self._last_fetch_time[ticker] = now
        
        db_fallback_bar = Bar(
            ticker=fallback_bar.ticker,
            timestamp=datetime.combine(timestamp.date(), datetime.min.time()),
            open=fallback_bar.open,
            high=fallback_bar.high,
            low=fallback_bar.low,
            close=fallback_bar.close,
            volume=fallback_bar.volume
        )
        await clickhouse_manager.save_bar(db_fallback_bar)
        await event_bus.publish(RawDataCollectedEvent(ticker=ticker, bar=fallback_bar))
        logger.warning("Using offline deterministic fallback in DataCollector due to API failure", ticker=ticker)
        return fallback_bar

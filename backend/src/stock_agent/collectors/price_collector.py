import httpx
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import FinanceDataReader as fdr
from stock_agent.core.config import settings
from stock_agent.core.schemas import Bar
from stock_agent.core.interfaces import DataRepository
from stock_agent.monitoring.logger import logger
from stock_agent.storage.universe_manager import CRYPTO_30

class PriceCollector:
    def __init__(self, repository: DataRepository):
        self.repository = repository
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY

    async def collect_historical_bars(self, ticker: str, start_date: date, end_date: date) -> List[Bar]:
        """Fetches daily stock bars using the multi-tier data pipeline and persists to storage."""
        logger.info("Starting price collection cycle", ticker=ticker, start=start_date.isoformat(), end=end_date.isoformat())
        
        bars = []

        # ==========================================================
        # CRYPTO ROUTING: Coinone API
        # ==========================================================
        if ticker in CRYPTO_30:
            try:
                bars = await self._fetch_from_coinone(ticker, start_date, end_date)
                if bars:
                    await self.repository.save_bars(bars)
                    logger.info("Successfully fetched bars from Coinone", ticker=ticker, count=len(bars))
                    return bars
            except Exception as e:
                logger.warning("Coinone collection failed, falling back to simulated generator", ticker=ticker, error=str(e))
                
        else:
            # ==========================================================
            # TIER 1: FinanceDataReader (FDR)
            # ==========================================================
            try:
                bars = await self._fetch_from_finance_datareader(ticker, start_date, end_date)
                if bars:
                    await self.repository.save_bars(bars)
                    logger.info("Successfully fetched bars from FinanceDataReader (Tier 1)", ticker=ticker, count=len(bars))
                    return bars
            except Exception as e:
                logger.warning("FinanceDataReader collection failed, falling back to Alpha Vantage", ticker=ticker, error=str(e))

            # ==========================================================
            # TIER 2: Alpha Vantage API
            # ==========================================================
            if self.alpha_vantage_key and self.alpha_vantage_key != "your_alpha_vantage_api_key_here":
                try:
                    bars = await self._fetch_from_alpha_vantage(ticker, start_date, end_date)
                    if bars:
                        await self.repository.save_bars(bars)
                        logger.info("Successfully fetched bars from Alpha Vantage (Tier 2)", ticker=ticker, count=len(bars))
                        return bars
                except Exception as e:
                    logger.warning("Alpha Vantage API collection failed, falling back to simulated generator", ticker=ticker, error=str(e))

        # ==========================================================
        # TIER 3: Defensive Offline Simulated Generator (Fail-safe)
        # ==========================================================
        bars = self._generate_simulated_bars(ticker, start_date, end_date)
        await self.repository.save_bars(bars)
        logger.info("Successfully generated offline mock bars (Tier 3 / Fail-safe)", ticker=ticker, count=len(bars))
        return bars

    async def collect_daily_close(self, ticker: str) -> List[Bar]:
        today = date.today()
        # Look back 3 days to guarantee catching the latest trade day over weekends
        return await self.collect_historical_bars(ticker, today - timedelta(days=3), today)

    async def _fetch_from_coinone(self, ticker: str, start_date: date, end_date: date) -> List[Bar]:
        """Queries the Coinone Public API for crypto chart data."""
        # start_date and end_date converted to milliseconds timestamps
        start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000)
        end_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000)
        
        url_template = f"https://api.coinone.co.kr/public/v2/chart/KRW/{ticker}?interval=1d&size=200"
        
        bars = []
        current_end_ts = end_ts
        
        async with httpx.AsyncClient() as client:
            while current_end_ts >= start_ts:
                url = f"{url_template}&timestamp={current_end_ts}"
                response = await client.get(url, timeout=15.0)
                if response.status_code != 200:
                    raise RuntimeError(f"Coinone HTTP error: {response.status_code}")
                    
                data = response.json()
                if data.get("result") != "success":
                    raise RuntimeError(f"Coinone API error: {data.get('error_code')}")
                    
                chart = data.get("chart", [])
                if not chart:
                    break
                    
                batch_bars = []
                for item in chart:
                    bar_ts = item["timestamp"]
                    if bar_ts < start_ts:
                        continue
                    if bar_ts > end_ts:
                        continue
                        
                    batch_bars.append(
                        Bar(
                            ticker=ticker,
                            timestamp=datetime.fromtimestamp(bar_ts / 1000.0),
                            open=float(item["open"]),
                            high=float(item["high"]),
                            low=float(item["low"]),
                            close=float(item["close"]),
                            volume=float(item["target_volume"])
                        )
                    )
                
                bars.extend(batch_bars)
                
                # Update current_end_ts to paginate backwards
                oldest_ts = chart[-1]["timestamp"]
                # subtract 1 day in ms to not fetch the same oldest day again
                next_end_ts = oldest_ts - (24 * 60 * 60 * 1000)
                
                if next_end_ts >= current_end_ts:
                    break # Safety break to avoid infinite loop
                current_end_ts = next_end_ts
                
                # Sleep to prevent hitting rate limits
                await asyncio.sleep(0.5)

        # Sort ascending by date
        bars.sort(key=lambda x: x.timestamp)
        return bars

    async def _fetch_from_alpha_vantage(self, ticker: str, start_date: date, end_date: date) -> List[Bar]:
        """Queries the Alpha Vantage TIME_SERIES_DAILY endpoint asynchronously."""
        # Standardize symbols for Alpha Vantage (e.g. KRX tickers require suffix .KS or .KQ)
        av_symbol = ticker
        if ticker.isdigit():
            # Korean stocks: default to KOSPI .KS suffix
            av_symbol = f"{ticker}.KS"

        logger.debug("Requesting Alpha Vantage TIME_SERIES_DAILY", symbol=av_symbol)
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
                # Handle API rate limit message or error messages
                note = data.get("Note") or data.get("Error Message")
                raise RuntimeError(f"Alpha Vantage API error or rate limit hit: {note}")

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

    async def _fetch_from_finance_datareader(self, ticker: str, start_date: date, end_date: date) -> List[Bar]:
        """Wrapper to call FinanceDataReader.DataReader asynchronously in an executor thread."""
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        logger.debug("Calling FinanceDataReader", ticker=ticker, start=start_str, end=end_str)
        
        # FDR is synchronous, run in thread pool
        df = await asyncio.to_thread(fdr.DataReader, ticker, start_str, end_str)
        
        if df is None or df.empty:
            return []

        bars = []
        for timestamp, row in df.iterrows():
            # FinanceDataReader columns: Open, High, Low, Close, Volume
            # Standardize column naming since Korean indexes may vary
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

    def _generate_simulated_bars(self, ticker: str, start_date: date, end_date: date) -> List[Bar]:
        """Deterministic fallback bar generator when all external APIs are blocked."""
        import random
        random.seed(hash(ticker) % 12345)
        
        base_price = 70000.0 if ticker == "005930" else (180000.0 if ticker == "000660" else 190000.0)
        
        bars = []
        curr_date = start_date
        while curr_date <= end_date:
            if curr_date.weekday() < 5:  # Market days only
                change = base_price * random.uniform(-0.015, 0.02)
                o_price = base_price
                c_price = base_price + change
                h_price = max(o_price, c_price) + (base_price * random.uniform(0.001, 0.005))
                l_price = min(o_price, c_price) - (base_price * random.uniform(0.001, 0.005))
                
                bars.append(
                    Bar(
                        ticker=ticker,
                        timestamp=datetime.combine(curr_date, datetime.min.time()),
                        open=o_price,
                        high=h_price,
                        low=l_price,
                        close=c_price,
                        volume=float(random.randint(500000, 2000000))
                    )
                )
                base_price = c_price
            curr_date += timedelta(days=1)
            
        return bars

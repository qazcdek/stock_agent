import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import vectorbt as vbt

# Ensure the backend src/ directory is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from stock_agent.storage.repository import storage_layer
from stock_agent.common.dto import Bar
from stock_agent.common.logger import logger

def run_bollinger_bands_backtest(
    ticker: str, 
    start_dt: datetime, 
    end_dt: datetime, 
    window: int = 20, 
    num_std: float = 2.0,
    initial_cash: float = 100000000.0,
    commission: float = 0.00015
):
    """
    Example Bollinger Bands strategy backtest using vectorbt.
    
    Strategy Rules:
    - BUY (Entry) when price crosses BELOW the lower Bollinger Band (Oversold).
    - SELL (Exit) when price crosses ABOVE the upper Bollinger Band (Overbought).
    """
    print(f"=== Running Bollinger Bands Backtest for {ticker} ===")
    print(f"Period: {start_dt.date()} to {end_dt.date()}")
    print(f"Params: Window={window}, StdDev={num_std}, Cash=KRW {initial_cash:,.0f}\n")
    
    # 1. Fetch bars from SQL database
    bars = storage_layer.get_bars(
        ticker, 
        limit=100000, 
        start_date=start_dt.isoformat(), 
        end_date=end_dt.isoformat(),
        sort_desc=False # Ascending order (oldest first)
    )
    
    if not bars:
        print(f"No database bars found for {ticker}. Seeding mock bars to run example...")
        bars = generate_mock_bars(ticker, start_dt, end_dt)
        # Save mock bars to SQLite database
        for b in bars:
            storage_layer.save_bar(b)
            
    # 2. Convert database bars into a pandas DataFrame
    df_data = [{"Date": b.timestamp, "Close": b.close} for b in bars]
    df = pd.DataFrame(df_data)
    df.set_index("Date", inplace=True)
    
    # 3. Calculate Bollinger Bands indicators
    close_series = df["Close"]
    sma = close_series.rolling(window=window).mean()
    rstd = close_series.rolling(window=window).std()
    
    upper_band = sma + num_std * rstd
    lower_band = sma - num_std * rstd
    
    # Fill NaNs to avoid false signals
    upper_band = upper_band.fillna(close_series.max() * 1.5)
    lower_band = lower_band.fillna(0.0)
    
    # 4. Generate Strategy Signal Masks
    # Enter when Close goes below Lower Band
    entries = close_series < lower_band
    # Exit when Close goes above Upper Band
    exits = close_series > upper_band
    
    # Clean up index frequency to prevent pandas/vectorbt BusinessDay ('B') conversion crashes
    df.index = df.index.astype(str)
    entries.index = entries.index.astype(str)
    exits.index = exits.index.astype(str)
    
    # 5. Run vectorbt Portfolio simulation
    pf = vbt.Portfolio.from_signals(
        df["Close"],
        entries=entries,
        exits=exits,
        init_cash=initial_cash,
        fees=commission,
        freq='d' # Treat as daily frequency
    )
    
    # 6. Print Report Metrics
    stats = pf.stats()
    print("=== Backtest Performance Statistics ===")
    print(stats.to_string())
    print("=======================================")


def generate_mock_bars(ticker: str, start_dt: datetime, end_dt: datetime) -> list:
    """Generates synthetic price bars for dry-runs if database is empty."""
    import random
    random.seed(12345)
    
    bars = []
    curr_dt = start_dt
    base_price = 70000.0
    
    while curr_dt <= end_dt:
        if curr_dt.weekday() < 5:  # Weekdays only
            change = base_price * random.uniform(-0.02, 0.02)
            close_val = base_price + change
            
            bars.append(
                Bar(
                    ticker=ticker,
                    timestamp=curr_dt,
                    open=base_price,
                    high=max(base_price, close_val) + 200.0,
                    low=min(base_price, close_val) - 200.0,
                    close=close_val,
                    volume=float(random.randint(500000, 2000000))
                )
            )
            base_price = close_val
        curr_dt += timedelta(days=1)
        
    return bars


if __name__ == "__main__":
    # Configure storage layer to write to a local file
    storage_layer.use_db("stock_agent.db")
    
    target_ticker = "005930"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    run_bollinger_bands_backtest(
        ticker=target_ticker,
        start_dt=start_date,
        end_dt=end_date
    )

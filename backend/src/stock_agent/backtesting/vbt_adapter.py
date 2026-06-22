import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime
from typing import Dict, Any, List
from stock_agent.storage.repository import storage_layer
from stock_agent.common.logger import logger

class VBTBacktestRunner:
    async def run_backtest(
        self, 
        tickers: List[str], 
        start_dt: datetime, 
        end_dt: datetime, 
        initial_cash: float = 100000000.0,
        commission: float = 0.00015,
        repository: Any = None,
        strategy: str = "technical"
    ) -> Dict[str, Any]:
        """Runs a vectorized backtest using vectorbt for the specified tickers."""
        logger.info("Initializing vectorbt backtest", tickers=tickers, start=start_dt.isoformat(), end=end_dt.isoformat())
        
        repo = repository or storage_layer
        
        ticker_dfs = {}
        for ticker in tickers:
            # Fetch bars from storage layer
            import inspect
            if hasattr(repo, "get_bars") and inspect.iscoroutinefunction(repo.get_bars):
                bars = await repo.get_bars(ticker, start_dt, end_dt)
            else:
                bars = repo.get_bars(
                    ticker, 
                    limit=100000, 
                    start_date=start_dt.isoformat(), 
                    end_date=end_dt.isoformat(),
                    sort_desc=False # Chronological (ascending) order
                )
            
            if not bars:
                logger.warn("No bars found in repository for vectorbt backtesting", ticker=ticker)
                continue
                
            df_data = []
            for b in bars:
                df_data.append({
                    "Date": b.timestamp,
                    "Close": b.close
                })
            df = pd.DataFrame(df_data)
            df.set_index("Date", inplace=True)
            ticker_dfs[ticker] = df
            
        if not ticker_dfs:
            logger.error("No historical bars found in repository for any tickers for backtesting")
            return {"error": "No data found for tickers"}
            
        # Combine close prices into a single DataFrame
        close_df = pd.DataFrame()
        for ticker, df in ticker_dfs.items():
            close_df[ticker] = df["Close"]
            
        # Forward fill and backward fill missing prices
        close_df = close_df.ffill().bfill()
        
        # Determine frequency from DatetimeIndex before converting index to string
        from datetime import timedelta
        freq = 'd'
        if len(close_df) > 1:
            try:
                diff = close_df.index[1] - close_df.index[0]
                if diff <= timedelta(minutes=20):
                    freq = '15T'
                elif diff <= timedelta(hours=2):
                    freq = 'h'
                else:
                    freq = 'd'
            except Exception:
                freq = 'd'
        
        # Convert index to string to completely prevent BusinessDay ('B') conversion crashes in vectorbt
        close_df.index = close_df.index.astype(str)
        
        # Calculate indicator-based entries and exits for each ticker
        entries = pd.DataFrame(index=close_df.index, columns=close_df.columns, dtype=bool)
        exits = pd.DataFrame(index=close_df.index, columns=close_df.columns, dtype=bool)
        
        for ticker in close_df.columns:
            close_series = close_df[ticker]
            
            if strategy == "bollinger":
                # Bollinger Bands Breakout Strategy (Example)
                window = 20
                num_std = 2.0
                sma = close_series.rolling(window=window).mean()
                rstd = close_series.rolling(window=window).std()
                upper_band = (sma + num_std * rstd).fillna(close_series.max() * 1.5)
                lower_band = (sma - num_std * rstd).fillna(0.0)
                
                buy_sig = close_series < lower_band
                sell_sig = close_series > upper_band
            else:
                # Default Technical SMA/RSI Crossover Strategy
                sma_5 = close_series.rolling(window=5).mean()
                sma_20 = close_series.rolling(window=20).mean()
                
                delta = close_series.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / (loss + 1e-9)
                rsi = 100 - (100 / (1 + rs))
                
                # Fill NaNs to prevent false signals or errors
                sma_5 = sma_5.fillna(close_series)
                sma_20 = sma_20.fillna(close_series)
                rsi = rsi.fillna(50.0)
                
                # Technical Strategy Logic (aligns with TechnicalAnalyst in blackboard)
                buy_sig = ((rsi < 35) & (sma_5 >= sma_20)) | (rsi < 40)
                sell_sig = ((rsi > 65) & (sma_5 <= sma_20)) | (rsi > 60)
            
            entries[ticker] = buy_sig
            exits[ticker] = sell_sig
            
        try:
            # Divide initial cash among all tickers
            cash_per_ticker = initial_cash / len(close_df.columns)

            # Run vectorbt simulation
            pf = vbt.Portfolio.from_signals(
                close_df,
                entries=entries,
                exits=exits,
                init_cash=cash_per_ticker,
                fees=commission,
                freq=freq
            )
            
            # Extract cumulative performance stats
            value_data = pf.value()
            if isinstance(value_data, pd.DataFrame):
                final_value = float(value_data.sum(axis=1).iloc[-1])
            else:
                final_value = float(value_data.iloc[-1])

            total_return_ratio = pf.total_return()
            max_dd_ratio = pf.max_drawdown()
            sharpe_val = pf.sharpe_ratio()
            
            # If multi-ticker, vectorbt returns a Series per metric. We average them.
            if isinstance(total_return_ratio, pd.Series):
                total_return_pct = float(total_return_ratio.mean() * 100.0)
                max_dd_pct = float(max_dd_ratio.mean() * 100.0)
                sharpe = float(sharpe_val.mean())
            else:
                total_return_pct = float(total_return_ratio * 100.0)
                max_dd_pct = float(max_dd_ratio * 100.0)
                sharpe = float(sharpe_val)
                
            if np.isnan(sharpe) or np.isinf(sharpe):
                sharpe = 0.0
                
            steps_run = len(close_df)
            
            logger.info(
                "Vectorbt backtest completed successfully",
                final_value=final_value,
                return_pct=total_return_pct,
                mdd=max_dd_pct,
                sharpe=sharpe
            )
            
            return {
                "tickers": list(close_df.columns),
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "steps_run": steps_run,
                "final_value": round(final_value, 2),
                "return_pct": round(total_return_pct, 3),
                "mdd": round(max_dd_pct, 2),
                "sharpe_ratio": round(sharpe, 2)
            }
            
        except Exception as ex:
            logger.error("Vectorbt Portfolio execution failed", error=str(ex))
            return {"error": f"vectorbt execution failed: {str(ex)}"}

# Global vectorbt runner instance
vbt_backtest_runner = VBTBacktestRunner()

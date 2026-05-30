import numpy as np
import pandas as pd
from typing import Dict, Any, List
from stock_agent.common.dto import RawDataCollectedEvent, FeaturesComputedEvent, Bar
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.storage.repository import storage_layer
from stock_agent.infra.storage.multi_db import duckdb_manager


class Preprocessor:
    def __init__(self):
        # Register automatic event listener to RawDataCollectedEvent
        event_bus.subscribe("RawDataCollected", self.on_raw_data_collected)
        logger.info("Preprocessor initialized and subscribed to RawDataCollectedEvent")

    async def on_raw_data_collected(self, event: RawDataCollectedEvent):
        """Callback for when raw data is collected."""
        ticker = event.ticker
        bar = event.bar
        
        # Pull history from storage
        bars = storage_layer.get_bars(ticker, limit=50)
        
        if len(bars) < 5:
            # Not enough data yet to compute technical features
            logger.debug("Skipping feature computation, insufficient bars", ticker=ticker, count=len(bars))
            return
            
        features = self.compute_indicators(bars)
        
        # Save features back to DuckDB
        await duckdb_manager.save_features(ticker, bar.timestamp, features)
        
        # Publish FeaturesComputedEvent
        out_event = FeaturesComputedEvent(ticker=ticker, bar=bar, features=features)
        await event_bus.publish(out_event)

    def compute_indicators(self, bars: List[Bar]) -> Dict[str, Any]:
        """Compute SMA_5, SMA_20, RSI_14 indicators using pandas."""
        df = pd.DataFrame([b.model_dump() for b in bars])
        
        # Core Technical Indicators
        df["sma_5"] = df["close"].rolling(window=min(5, len(df))).mean()
        df["sma_20"] = df["close"].rolling(window=min(20, len(df))).mean()
        
        # Simple RSI implementation
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=min(14, len(df)-1)).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=min(14, len(df)-1)).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        df["rsi"] = rsi
        
        # Momentum/Volatility
        df["volatility_5"] = df["close"].rolling(window=min(5, len(df))).std()
        
        # Extract latest record values
        latest = df.iloc[-1]
        
        return {
            "sma_5": float(latest["sma_5"]) if not pd.isna(latest["sma_5"]) else float(latest["close"]),
            "sma_20": float(latest["sma_20"]) if not pd.isna(latest["sma_20"]) else float(latest["close"]),
            "rsi": float(latest["rsi"]) if not pd.isna(latest["rsi"]) else 50.0,
            "volatility_5": float(latest["volatility_5"]) if not pd.isna(latest["volatility_5"]) else 0.0,
            "close": float(latest["close"])
        }
pip_preprocessor = Preprocessor()

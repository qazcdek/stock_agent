import numpy as np
from typing import Dict, Any, List
from stock_agent.common.logger import logger
from stock_agent.storage.repository import storage_layer


class MLSystem:
    def __init__(self):
        # We store model weights (slope and intercept) per ticker
        self.models: Dict[str, Dict[str, float]] = {}
        logger.info("ML System initialized")

    def train(self, ticker: str) -> bool:
        """Train a quick linear regression model using ordinary least squares (OLS) on historical bars."""
        bars = storage_layer.get_bars(ticker, limit=30)
        if len(bars) < 10:
            logger.warn("Cannot train ML Model, insufficient historical bars", ticker=ticker, count=len(bars))
            return False

        prices = [b.close for b in bars]
        n = len(prices)
        
        # X is time indices [0, 1, 2, ..., n-1]
        x = np.arange(n)
        y = np.array(prices)
        
        # OLS Linear Regression Formula: y = slope * x + intercept
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        num = np.sum((x - x_mean) * (y - y_mean))
        den = np.sum((x - x_mean) ** 2)
        
        if den == 0:
            slope = 0.0
            intercept = y_mean
        else:
            slope = num / den
            intercept = y_mean - slope * x_mean
            
        self.models[ticker] = {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(num**2 / (den * np.sum((y - y_mean)**2) + 1e-9))
        }
        
        logger.info("ML Model trained successfully", ticker=ticker, slope=slope, intercept=intercept)
        return True

    def predict(self, ticker: str) -> Dict[str, Any]:
        """Perform real-time inference on the next bar's close price."""
        # Ensure model is trained, if not try to train
        if ticker not in self.models:
            success = self.train(ticker)
            if not success:
                # Return naive current close as prediction
                latest_bar = storage_layer.get_cache(f"latest_bar:{ticker}")
                latest_close = latest_bar.close if latest_bar else 100.0
                return {
                    "ticker": ticker,
                    "predicted_close": latest_close,
                    "direction": "HOLD",
                    "confidence": 0.5
                }

        # Calculate inference
        bars = storage_layer.get_bars(ticker, limit=30)
        n = len(bars)
        model = self.models[ticker]
        
        # The next index is `n`
        predicted_close = model["slope"] * n + model["intercept"]
        latest_close = bars[-1].close if bars else predicted_close
        
        price_diff = predicted_close - latest_close
        pct_change = price_diff / (latest_close + 1e-9)
        
        if pct_change > 0.002: # predicted price rises by 0.2%
            direction = "BUY"
        elif pct_change < -0.002:
            direction = "SELL"
        else:
            direction = "HOLD"
            
        confidence = min(0.95, max(0.5, 0.5 + abs(pct_change) * 20))
        
        logger.debug("ML Model predicted price", ticker=ticker, current=latest_close, predicted=predicted_close, direction=direction)
        
        return {
            "ticker": ticker,
            "predicted_close": round(float(predicted_close), 2),
            "direction": direction,
            "confidence": round(float(confidence), 3)
        }


# Global ML System Instance
ml_system = MLSystem()

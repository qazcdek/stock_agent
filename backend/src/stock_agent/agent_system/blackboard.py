from datetime import datetime
from typing import Dict, List, Any
from stock_agent.common.dto import FeaturesComputedEvent, SignalCandidate, ActionType
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.ml_system.predictor import ml_system


class Blackboard:
    """Shared state container where agents publish their analysis and signal proposals."""
    def __init__(self):
        # Maps ticker -> list of SignalCandidate
        self._data: Dict[str, List[SignalCandidate]] = {}

    def clear(self, ticker: str):
        self._data[ticker] = []

    def write(self, ticker: str, candidate: SignalCandidate):
        if ticker not in self._data:
            self._data[ticker] = []
        self._data[ticker].append(candidate)

    def read(self, ticker: str) -> List[SignalCandidate]:
        return self._data.get(ticker, []).copy()


class TechnicalAnalyst:
    def analyze(self, ticker: str, timestamp: datetime, features: dict) -> SignalCandidate:
        rsi = features.get("rsi", 50.0)
        sma_5 = features.get("sma_5", 1.0)
        sma_20 = features.get("sma_20", 1.0)
        
        action = ActionType.HOLD
        reason = "Technical indicators are neutral."
        weight = 0.5

        # Combine RSI and Moving Average Crossovers
        if rsi < 35 and sma_5 >= sma_20:
            action = ActionType.BUY
            reason = f"Oversold RSI ({rsi:.1f}) and Golden Crossover (SMA5 > SMA20)."
            weight = 0.85
        elif rsi > 65 and sma_5 <= sma_20:
            action = ActionType.SELL
            reason = f"Overbought RSI ({rsi:.1f}) and Death Crossover (SMA5 < SMA20)."
            weight = 0.85
        elif rsi < 40:
            action = ActionType.BUY
            reason = f"RSI indicates oversold conditions ({rsi:.1f})."
            weight = 0.65
        elif rsi > 60:
            action = ActionType.SELL
            reason = f"RSI indicates overbought conditions ({rsi:.1f})."
            weight = 0.65

        return SignalCandidate(
            ticker=ticker,
            timestamp=timestamp,
            action=action,
            source_agent="TechnicalAnalyst",
            weight=weight,
            reason=reason
        )


class FundamentalAnalyst:
    def __init__(self):
        # Simulated fundamental scores
        self._health_scores = {
            "005930": {"pe": 12.5, "roe": 15.0, "status": "Under-valued health"},
            "035720": {"pe": 35.2, "roe": 6.5, "status": "Growth momentum"},
            "BTC": {"pe": 0.0, "roe": 0.0, "status": "Speculative high demand"}
        }

    def analyze(self, ticker: str, timestamp: datetime) -> SignalCandidate:
        score = self._health_scores.get(ticker, {"pe": 15.0, "roe": 10.0, "status": "Average"})
        
        # Simple fundamental rule
        if ticker == "BTC":
            action = ActionType.HOLD
            reason = "Cryptocurrency fundamental is hard to model. Deferring to other agents."
            weight = 0.1
        elif score["pe"] < 15.0 and score["roe"] > 12.0:
            action = ActionType.BUY
            reason = f"Fundamental analysis shows low PE ({score['pe']}) and solid ROE ({score['roe']}%) - highly undervalued."
            weight = 0.75
        elif score["pe"] > 30.0:
            action = ActionType.SELL
            reason = f"High PE ratio ({score['pe']}) suggests premium valuation."
            weight = 0.6
        else:
            action = ActionType.HOLD
            reason = "Valuation is fair, robust asset health."
            weight = 0.5

        return SignalCandidate(
            ticker=ticker,
            timestamp=timestamp,
            action=action,
            source_agent="FundamentalAnalyst",
            weight=weight,
            reason=reason
        )


class MLAnalyst:
    def analyze(self, ticker: str, timestamp: datetime) -> SignalCandidate:
        # Perform predictive inference via ML System
        prediction = ml_system.predict(ticker)
        
        action = ActionType(prediction["direction"])
        weight = prediction["confidence"]
        predicted_close = prediction["predicted_close"]
        
        return SignalCandidate(
            ticker=ticker,
            timestamp=timestamp,
            action=action,
            source_agent="MLAnalyst",
            weight=weight,
            reason=f"ML regression model forecasts next price around {predicted_close} (confidence: {weight*100:.1f}%)."
        )


class BlackboardAgentSystem:
    def __init__(self):
        self.blackboard = Blackboard()
        self.tech_analyst = TechnicalAnalyst()
        self.fund_analyst = FundamentalAnalyst()
        self.ml_analyst = MLAnalyst()
        
        # Subscribe to FeaturesComputedEvent
        event_bus.subscribe("FeaturesComputed", self.on_features_computed)
        logger.info("BlackboardAgentSystem initialized and subscribed to FeaturesComputedEvent")

    async def on_features_computed(self, event: FeaturesComputedEvent):
        ticker = event.ticker
        timestamp = event.bar.timestamp
        features = event.features

        # Clear blackboard slice for this ticker run
        self.blackboard.clear(ticker)

        # 1. Technical Analyst runs and writes to blackboard
        tech_sig = self.tech_analyst.analyze(ticker, timestamp, features)
        self.blackboard.write(ticker, tech_sig)

        # 2. Fundamental Analyst runs and writes to blackboard
        fund_sig = self.fund_analyst.analyze(ticker, timestamp)
        self.blackboard.write(ticker, fund_sig)

        # 3. ML Analyst runs and writes to blackboard
        ml_sig = self.ml_analyst.analyze(ticker, timestamp)
        self.blackboard.write(ticker, ml_sig)

        logger.info("Blackboard populated with analyst signals", ticker=ticker, timestamp=timestamp.isoformat())
        
        # Triggers strategy analysis next
        await event_bus.publish(BlackboardUpdatedEvent(ticker=ticker, timestamp=timestamp))


class BlackboardUpdatedEvent(FeaturesComputedEvent):
    event_type: str = "BlackboardUpdated"
    ticker: str
    timestamp: datetime
    # Inherit Pydantic fields or build cleanly
    bar: Any = None
    features: Any = None


# Global Blackboard Agent System Instance
blackboard_agent_system = BlackboardAgentSystem()

from datetime import datetime
from stock_agent.common.dto import ActionType, OrderIntent, OrderIntentGeneratedEvent
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.agent_system.blackboard import blackboard_agent_system, BlackboardUpdatedEvent
from stock_agent.storage.repository import storage_layer


class StrategyEngine:
    def __init__(self):
        event_bus.subscribe("BlackboardUpdated", self.on_blackboard_updated)
        logger.info("StrategyEngine initialized and subscribed to BlackboardUpdatedEvent")

    async def on_blackboard_updated(self, event: BlackboardUpdatedEvent):
        ticker = event.ticker
        timestamp = event.timestamp

        # Read signal candidates from blackboard
        candidates = blackboard_agent_system.blackboard.read(ticker)
        if not candidates:
            logger.warn("StrategyEngine received blackboard update but no candidates found", ticker=ticker)
            return

        # Weight synthesis rules
        # TechnicalAnalyst = 0.35 weight
        # FundamentalAnalyst = 0.15 weight
        # MLAnalyst = 0.50 weight
        weights = {
            "TechnicalAnalyst": 0.35,
            "FundamentalAnalyst": 0.15,
            "MLAnalyst": 0.50
        }

        score = 0.0
        details = []

        for cand in candidates:
            # Action score multiplier
            mult = 0.0
            if cand.action == ActionType.BUY:
                mult = 1.0
            elif cand.action == ActionType.SELL:
                mult = -1.0
            
            w = weights.get(cand.source_agent, 0.3)
            contrib = cand.weight * mult * w
            score += contrib
            details.append(f"{cand.source_agent}({cand.action.value}, wt={cand.weight:.2f}) contrib={contrib:.2f}")

        latest_bar = storage_layer.get_cache(f"latest_bar:{ticker}")
        price = latest_bar.close if latest_bar else 100.0

        decision = ActionType.HOLD
        # Synthesis Thresholds
        if score >= 0.25:
            decision = ActionType.BUY
        elif score <= -0.25:
            decision = ActionType.SELL

        logger.info(
            "Strategy synthesised signals",
            ticker=ticker,
            score=score,
            decision=decision.value,
            agents=", ".join(details)
        )

        if decision != ActionType.HOLD:
            # Calculate dynamic sizing
            # Simple rule: buy/sell fixed dollar amount (e.g. 5,000,000 KRW for Bitcoin, or 10 shares for stocks)
            quantity = 1
            if ticker == "BTC":
                # For bitcoin buy tiny fraction or round count
                quantity = max(1, int(10000000 / price)) # ~10,000,000 KRW worth of BTC
            else:
                quantity = 10 # 10 shares for standard stocks

            intent = OrderIntent(
                ticker=ticker,
                action=decision,
                quantity=quantity,
                price=price,
                timestamp=timestamp,
                source_strategy="SynthesizedBlackboardStrategy"
            )

            # Publish OrderIntentGeneratedEvent
            out_event = OrderIntentGeneratedEvent(intent=intent)
            await event_bus.publish(out_event)


# Global Strategy Engine Instance
strategy_engine = StrategyEngine()

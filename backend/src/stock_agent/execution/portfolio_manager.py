from datetime import datetime
from typing import Dict, List, Tuple
from stock_agent.core.config import settings
from stock_agent.core.enums import Action
from stock_agent.core.schemas import PortfolioState, Position, Signal
from stock_agent.core.interfaces import Broker, DataRepository
from stock_agent.monitoring.logger import logger

class PortfolioManager:
    def __init__(self, broker: Broker, repository: DataRepository):
        self.broker = broker
        self.repository = repository

    async def sync_and_snapshot(self) -> PortfolioState:
        """Syncs latest account weights from broker, calculates real-time PnL, and snapshots to storage."""
        logger.info("Synchronizing portfolio state with broker...")
        
        # 1. Fetch live metrics from broker
        balance_data = await self.broker.get_balance()
        cash = balance_data.get("cash", 0.0)
        
        positions = await self.broker.get_positions()
        
        # 2. Update real-time valuations for each holding
        total_holdings_value = 0.0
        updated_positions: Dict[str, Position] = {}
        
        for ticker, pos in positions.items():
            current_price = await self.broker.get_current_price(ticker)
            
            # Recalculate valuations
            avg_price = pos.avg_price
            qty = pos.quantity
            
            pnl = (current_price - avg_price) * qty
            pnl_pct = ((current_price - avg_price) / (avg_price + 1e-9))
            
            updated_pos = Position(
                ticker=ticker,
                quantity=qty,
                avg_price=avg_price,
                current_price=current_price,
                pnl=pnl,
                pnl_pct=pnl_pct
            )
            
            updated_positions[ticker] = updated_pos
            total_holdings_value += (qty * current_price)

        total_asset = cash + total_holdings_value
        
        state = PortfolioState(
            cash=cash,
            total_asset=total_asset,
            positions=updated_positions,
            timestamp=datetime.utcnow()
        )

        # 3. Snapshot state to database
        await self.repository.save_portfolio_state(state)
        logger.info("Portfolio state sync completed", total_assets=total_asset, cash=cash, active_holdings=len(updated_positions))
        return state

    def check_risk_thresholds(self, state: PortfolioState) -> List[Signal]:
        """Scans active holdings for stop-loss or take-profit breaches, outputting immediate liquidation suggestions."""
        liquidation_signals: List[Signal] = []

        for ticker, pos in state.positions.items():
            if pos.quantity <= 0:
                continue

            # Stop Loss check (default: -5%)
            if pos.pnl_pct <= -settings.RISK_STOP_LOSS_PCT:
                logger.warning("Stop-loss threshold breached! Initializing liquidation signal.", ticker=ticker, loss=f"{pos.pnl_pct*100:.2f}%")
                liquidation_signals.append(
                    Signal(
                        ticker=ticker,
                        action=Action.SELL,
                        confidence=1.0,
                        rationale=f"위험 제어: 손절선(-{settings.RISK_STOP_LOSS_PCT*100}%) 돌파에 따른 비상 전량 청산 매도 실행.",
                        timestamp=datetime.utcnow()
                    )
                )
            
            # Take Profit check (default: +15%)
            elif pos.pnl_pct >= settings.RISK_TAKE_PROFIT_PCT:
                logger.info("Take-profit threshold reached! Initializing harvest signal.", ticker=ticker, profit=f"{pos.pnl_pct*100:.2f}%")
                liquidation_signals.append(
                    Signal(
                        ticker=ticker,
                        action=Action.SELL,
                        confidence=0.9,
                        rationale=f"수익 보존: 목표 익절선(+{settings.RISK_TAKE_PROFIT_PCT*100}%) 도달에 따른 전량 분할/청산 매도 실행.",
                        timestamp=datetime.utcnow()
                    )
                )

        return liquidation_signals

import uuid
from datetime import datetime
from typing import Dict, List
from stock_agent.core.config import settings
from stock_agent.core.enums import Action, OrderType, OrderStatus
from stock_agent.core.schemas import Order, Signal, PortfolioState
from stock_agent.core.interfaces import Broker, DataRepository, LLMClient
from stock_agent.agents.synthesizer import SynthesizerAgent
from stock_agent.execution.position_sizer import PositionSizer
from stock_agent.execution.risk_gate import RiskGate
from stock_agent.execution.portfolio_manager import PortfolioManager
from stock_agent.monitoring.notifier import notifier
from stock_agent.monitoring.logger import logger

class StockTrader:
    def __init__(self, broker: Broker, repository: DataRepository, llm_client: LLMClient):
        self.broker = broker
        self.repository = repository
        self.portfolio_manager = PortfolioManager(broker, repository)
        self.synthesizer = SynthesizerAgent(repository, llm_client)
        self.sizer = PositionSizer()
        self.risk_gate = RiskGate()
        
        # Track daily traded amount (simplified in-memory state, can be loaded from DB on start)
        self.daily_traded_amount = 0.0
        self.last_traded_date = datetime.utcnow().date()

    async def execute_trade_cycle(self) -> None:
        """Executes a single end-to-end automated trading cycle."""
        logger.info("================ STARTING TRADE CYCLE ================")
        
        # Reset daily trade limits if new day started
        current_date = datetime.utcnow().date()
        if current_date != self.last_traded_date:
            logger.info("New trading day detected. Resetting daily traded limit tracker.")
            self.daily_traded_amount = 0.0
            self.last_traded_date = current_date

        try:
            # 1. Sync current portfolio state
            portfolio = await self.portfolio_manager.sync_and_snapshot()
            
            # 2. Risk check: Scan active positions for stop-loss or take-profit triggers
            defensive_signals = self.portfolio_manager.check_risk_thresholds(portfolio)
            if defensive_signals:
                logger.warning("Defensive liquidation signals triggered!", count=len(defensive_signals))
                for def_sig in defensive_signals:
                    await self._process_signal(def_sig, portfolio)
                # Sync portfolio state again after defensive liquidations
                portfolio = await self.portfolio_manager.sync_and_snapshot()

            # 3. Standard Analysis and trading for the target universe
            from stock_agent.storage.repository import get_trading_universe
            for ticker in get_trading_universe():
                logger.info("Analyzing universe constituent", ticker=ticker)
                
                # Check if ticker already triggered stop-loss in this cycle to avoid double trading
                if any(sig.ticker == ticker for sig in defensive_signals):
                    logger.debug("Skipping standard analysis for ticker since it was just defensively sold.", ticker=ticker)
                    continue
                
                try:
                    # Fetch master trade signal from multi-agent synthesis
                    signal = await self.synthesizer.generate_trade_signal(ticker)
                    await self._process_signal(signal, portfolio)
                except Exception as ex:
                    logger.error("Error occurred while generating signal for constituent", ticker=ticker, error=str(ex))
            
            logger.info("================ TRADE CYCLE COMPLETED SUCCESSFUL ================")
        except Exception as e:
            logger.critical("Critical crash in main trade cycle execution", error=str(e))
            await notifier.notify(f"🚨 <b>시스템 크리티컬 에러 발생:</b>\n{str(e)}")

    async def _process_signal(self, signal: Signal, portfolio: PortfolioState) -> None:
        """Translates a synthesized trade Signal into action and submits audited Orders to the broker."""
        ticker = signal.ticker
        action = signal.action
        
        if action == Action.HOLD:
            logger.info("Action is HOLD. No orders placed.", ticker=ticker)
            return

        current_price = await self.broker.get_current_price(ticker)
        
        if action == Action.BUY:
            # Calculate optimal target quantity
            qty = self.sizer.calculate_quantity(signal, portfolio, current_price)
            if qty <= 0:
                logger.info("Position size resolved to 0 units. Order cancelled.", ticker=ticker)
                return

            candidate_order = Order(
                order_id=str(uuid.uuid4()),
                ticker=ticker,
                action=action,
                order_type=OrderType.MARKET,
                quantity=qty,
                price=current_price,
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow()
            )

            # Pass through Risk Gate
            passed, reason = self.risk_gate.validate_order(candidate_order, portfolio, self.daily_traded_amount)
            if not passed:
                await notifier.notify(f"⚠️ <b>리스크 통제 차단 (매수 거부):</b> [{ticker}]\n사유: {reason}")
                return

            # Execute order at Broker
            await self._submit_order(candidate_order)

        elif action == Action.SELL:
            # For sells, liquidate the ENTIRE active position if held
            pos = portfolio.positions.get(ticker)
            if not pos or pos.quantity <= 0:
                logger.info("SELL signal received but no holding position found. Skipping.", ticker=ticker)
                return

            candidate_order = Order(
                order_id=str(uuid.uuid4()),
                ticker=ticker,
                action=action,
                order_type=OrderType.MARKET,
                quantity=pos.quantity,
                price=current_price,
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            # Submitting sell order
            await self._submit_order(candidate_order)

    async def _submit_order(self, order: Order) -> None:
        """Sends validated order to exchange, saves to database and pushes notifications."""
        logger.info("Dispatching order to broker", ticker=order.ticker, action=order.action, quantity=order.quantity)
        
        # Save order to DB as PENDING
        await self.repository.save_order(order)
        
        try:
            executed_order = await self.broker.place_order(order)
            
            # Save updated status (FILLED/REJECTED) to DB
            await self.repository.save_order(executed_order)
            
            order_val = executed_order.quantity * executed_order.price
            
            if executed_order.status == OrderStatus.FILLED:
                self.daily_traded_amount += order_val
                
                emoji = "🟢 [매수 체결]" if executed_order.action == Action.BUY else "🔴 [매도 체결]"
                msg = (
                    f"{emoji} <b>{executed_order.ticker}</b>\n"
                    f"수량: {executed_order.quantity}주 / 단가: {executed_order.price:,.0f}원\n"
                    f"총액: {order_val:,.0f}원\n"
                    f"상태: 체결 완료"
                )
                await notifier.notify(msg)
            else:
                await notifier.notify(f"❌ <b>주문 거부/실패:</b> {executed_order.ticker} ({executed_order.status.value})")

        except Exception as e:
            logger.error("Failed to execute broker order", ticker=order.ticker, error=str(e))
            await self.repository.update_order(order.order_id, OrderStatus.REJECTED)
            await notifier.notify(f"❌ <b>주문 실행 실패:</b> {order.ticker}\n에러: {str(e)}")

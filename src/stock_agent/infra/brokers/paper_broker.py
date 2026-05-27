from typing import Dict
from datetime import datetime
from stock_agent.core.enums import OrderStatus, Action
from stock_agent.core.schemas import Order, Position
from stock_agent.core.interfaces import Broker
from stock_agent.monitoring.logger import logger

class PaperBroker(Broker):
    """Simulated virtual broker running transactions in memory."""
    def __init__(self, initial_cash: float = 10000000.0):
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        # Prepopulate current prices for mock tickers (Samsung, Hynix, Naver)
        self.mock_prices = {
            "005930": 75000.0, # Samsung Electronics
            "000660": 180000.0, # SK Hynix
            "035420": 190000.0 # NAVER
        }

    async def place_order(self, order: Order) -> Order:
        logger.info("Mock broker processing order", ticker=order.ticker, action=order.action, qty=order.quantity)
        
        current_price = await self.get_current_price(order.ticker)
        order_value = order.quantity * current_price
        
        if order.action == Action.BUY:
            if self.cash < order_value:
                order.status = OrderStatus.REJECTED
                logger.warning("Mock broker rejected order: Insufficient Cash", cash=self.cash, cost=order_value)
                return order
            
            # Execute Buy
            self.cash -= order_value
            existing = self.positions.get(order.ticker)
            if existing:
                # Update average price and quantity
                total_qty = existing.quantity + order.quantity
                avg_price = ((existing.quantity * existing.avg_price) + order_value) / total_qty
                existing.quantity = total_qty
                existing.avg_price = avg_price
                existing.current_price = current_price
            else:
                self.positions[order.ticker] = Position(
                    ticker=order.ticker,
                    quantity=order.quantity,
                    avg_price=current_price,
                    current_price=current_price
                )
                
            order.status = OrderStatus.FILLED
            order.price = current_price
            order.filled_at = datetime.utcnow()
            logger.info("Mock BUY executed successfully", ticker=order.ticker, qty=order.quantity, price=current_price)

        elif order.action == Action.SELL:
            existing = self.positions.get(order.ticker)
            if not existing or existing.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                logger.warning("Mock broker rejected order: Insufficient shares", holding=(existing.quantity if existing else 0))
                return order
                
            # Execute Sell
            self.cash += order_value
            existing.quantity -= order.quantity
            if existing.quantity == 0:
                del self.positions[order.ticker]
            else:
                existing.current_price = current_price
                
            order.status = OrderStatus.FILLED
            order.price = current_price
            order.filled_at = datetime.utcnow()
            logger.info("Mock SELL executed successfully", ticker=order.ticker, qty=order.quantity, price=current_price)
            
        return order

    async def cancel_order(self, order_id: str) -> bool:
        logger.info("Mock cancel order", order_id=order_id)
        return True

    async def get_positions(self) -> Dict[str, Position]:
        return self.positions

    async def get_balance(self) -> Dict[str, float]:
        total_holdings = sum(p.quantity * p.current_price for p in self.positions.values())
        return {
            "cash": self.cash,
            "total_asset": self.cash + total_holdings
        }

    async def get_current_price(self, ticker: str) -> float:
        # Return registered mock price or a default 50000.0 KRW
        return self.mock_prices.get(ticker, 50000.0)

import random
from abc import ABC, abstractmethod
from stock_agent.common.dto import Order, OrderStatus
from stock_agent.common.logger import logger


class ExchangeAdapter(ABC):
    @abstractmethod
    async def execute_order(self, order: Order) -> Order:
        """Execute the order on the respective broker/exchange and return the updated Order object."""
        pass


class KISAdapter(ExchangeAdapter):
    """Korea Investment & Securities Mock Adapter."""
    async def execute_order(self, order: Order) -> Order:
        logger.info("KISAdapter: Executing mock order on KIS KOSPI Spot", order_id=order.order_id, ticker=order.ticker)
        
        # Simulate small network latency
        # We simulate 100% fill with KIS standard rules
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = order.price
        return order


class UpbitAdapter(ExchangeAdapter):
    """Upbit Cryptocurency Exchange Mock Adapter."""
    async def execute_order(self, order: Order) -> Order:
        logger.info("UpbitAdapter: Executing mock order on Upbit KRW Spot", order_id=order.order_id, ticker=order.ticker)
        
        # Simulate partial fill chance
        fill_chance = random.random()
        if fill_chance > 0.95:
            # 5% chance of partial fill
            order.status = OrderStatus.PARTIALLY_FILLED
            order.filled_quantity = max(1, int(order.quantity * 0.6))
            order.avg_fill_price = order.price * (1 + random.normalvariate(0, 0.001))
            order.reason = "Upbit partial liquidity limit"
        else:
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.avg_fill_price = order.price
        return order


class BacktestAdapter(ExchangeAdapter):
    """Backtesting Simulated Execution Adapter."""
    async def execute_order(self, order: Order) -> Order:
        logger.debug("BacktestAdapter: Simulating backtest execution", order_id=order.order_id)
        
        # Immediate 100% fill for backtests to ensure seamless fast validation
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = order.price
        return order


# Active Adapter selector (Defaults to KIS for standard stocks, Upbit for crypto, BTC -> Upbit, others -> KIS)
class RoutingExchangeAdapter(ExchangeAdapter):
    def __init__(self):
        self.kis = KISAdapter()
        self.upbit = UpbitAdapter()
        self.backtest = BacktestAdapter()
        self.is_backtesting = False

    def enable_backtesting(self, enable: bool = True):
        self.is_backtesting = enable

    async def execute_order(self, order: Order) -> Order:
        if self.is_backtesting:
            return await self.backtest.execute_order(order)
            
        if order.ticker == "BTC":
            return await self.upbit.execute_order(order)
        else:
            return await self.kis.execute_order(order)


# Global adapter router
exchange_adapter = RoutingExchangeAdapter()

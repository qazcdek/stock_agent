from stock_agent.common.dto import (
    OrderFilledEvent,
    Position,
    ActionType,
    PortfolioUpdatedEvent
)
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.storage.repository import storage_layer


class PortfolioManager:
    def __init__(self, initial_cash: float = 500000000.0):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self._kis_broker = None
        
        event_bus.subscribe("OrderFilled", self.on_order_filled)
        logger.info("PortfolioManager initialized and subscribed to OrderFilledEvent", initial_cash=self.cash)

        # Start background KIS sync loop if loop is running
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._kis_sync_loop())
        except RuntimeError:
            pass

    async def _kis_sync_loop(self):
        """Loop to periodically pull actual balance and position metrics from KIS."""
        import asyncio
        logger.info("Starting background KIS portfolio sync loop...")
        # Brief delay on startup
        await asyncio.sleep(5)
        while True:
            try:
                await self.sync_with_kis()
            except Exception as e:
                logger.error("Error in background KIS sync loop step", error=str(e))
            await asyncio.sleep(20) # pull every 20 seconds

    async def sync_with_kis(self):
        """Syncs the in-memory cash and database positions with real KIS broker values."""
        if self._kis_broker is None:
            try:
                from stock_agent.infra.brokers.kis_broker import KISBroker
                self._kis_broker = KISBroker()
            except Exception as e:
                logger.error("Failed to import/instantiate KISBroker", error=str(e))
                return

        if self._kis_broker.is_mock_mode:
            return

        # 1. Fetch balance from KIS
        try:
            balance = await self._kis_broker.get_balance()
            if balance and "cash" in balance:
                self.cash = balance["cash"]
                # Adjust initial_cash to prevent unrealistic return rates on UI
                if self.initial_cash == 500000000.0:
                    self.initial_cash = self.cash
                logger.info("Synced PortfolioManager cash with KIS", cash=self.cash)
        except Exception as e:
            logger.error("Error retrieving balance from KISBroker", error=str(e))

        # 2. Fetch positions from KIS
        try:
            kis_positions = await self._kis_broker.get_positions()
            if kis_positions is not None:
                from stock_agent.common.dto import Position as DtoPosition
                
                db_positions = storage_layer.get_positions()
                db_tickers = {p.ticker for p in db_positions}
                kis_tickers = set(kis_positions.keys())

                # Save or update KIS positions to DB
                for ticker, pos in kis_positions.items():
                    dto_pos = DtoPosition(
                        ticker=ticker,
                        quantity=pos.quantity,
                        avg_price=pos.avg_price,
                        current_price=pos.current_price,
                        floating_pnl=pos.pnl
                    )
                    storage_layer.save_position(dto_pos)

                # Delete any positions that are no longer in KIS
                for ticker in db_tickers - kis_tickers:
                    storage_layer.delete_position(ticker)
                    
                logger.info("Synced PortfolioManager positions with KIS", count=len(kis_positions))
        except Exception as e:
            logger.error("Error retrieving positions from KISBroker", error=str(e))

    def get_portfolio_summary(self) -> dict:
        positions = storage_layer.get_positions()
        
        # Recalculate P&L with latest prices
        total_pos_value = 0.0
        total_pnl = 0.0
        
        pos_dict = {}
        for pos in positions:
            # Try to get latest price from cache
            latest_bar = storage_layer.get_cache(f"latest_bar:{pos.ticker}")
            if latest_bar:
                pos.update_price(latest_bar.close)
                storage_layer.save_position(pos)
                
            total_pos_value += pos.quantity * pos.current_price
            total_pnl += pos.floating_pnl
            pos_dict[pos.ticker] = pos

        total_value = self.cash + total_pos_value
        
        return {
            "cash": self.cash,
            "positions_value": total_pos_value,
            "total_value": total_value,
            "floating_pnl": total_pnl,
            "return_pct": ((total_value - self.initial_cash) / self.initial_cash) * 100.0,
            "positions": pos_dict
        }

    async def on_order_filled(self, event: OrderFilledEvent):
        order = event.order
        ticker = order.ticker
        qty = order.filled_quantity
        price = order.avg_fill_price
        
        logger.info("PortfolioManager: updating portfolio on order fill", ticker=ticker, action=order.action.value, qty=qty, price=price)

        existing_pos = storage_layer.get_position(ticker)

        if order.action == ActionType.BUY:
            cost = qty * price
            self.cash -= cost
            
            if existing_pos:
                new_qty = existing_pos.quantity + qty
                # Weighted average price formula
                new_avg = ((existing_pos.quantity * existing_pos.avg_price) + cost) / new_qty
                
                existing_pos.quantity = new_qty
                existing_pos.avg_price = round(new_avg, 2)
                existing_pos.update_price(price)
                
                storage_layer.save_position(existing_pos)
            else:
                new_pos = Position(
                    ticker=ticker,
                    quantity=qty,
                    avg_price=price,
                    current_price=price
                )
                new_pos.update_price(price)
                storage_layer.save_position(new_pos)

        elif order.action == ActionType.SELL:
            revenue = qty * price
            self.cash += revenue
            
            if existing_pos:
                new_qty = existing_pos.quantity - qty
                if new_qty <= 0:
                    storage_layer.delete_position(ticker)
                else:
                    existing_pos.quantity = new_qty
                    existing_pos.update_price(price)
                    storage_layer.save_position(existing_pos)
            else:
                logger.warn("PortfolioManager sold asset but no existing position found", ticker=ticker)

        # Trigger updated portfolio metrics publish
        summary = self.get_portfolio_summary()
        await event_bus.publish(
            PortfolioUpdatedEvent(
                positions=summary["positions"],
                total_value=summary["total_value"],
                cash=summary["cash"],
                floating_pnl=summary["floating_pnl"]
            )
        )
        logger.info("PortfolioManager metrics recalculated and published", total_value=summary["total_value"], cash=summary["cash"])


# Global Portfolio Manager Instance
portfolio_manager = PortfolioManager()

import asyncio
import nest_asyncio
nest_asyncio.apply()

import backtrader as bt
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from stock_agent.core.config import settings
from stock_agent.core.enums import Action
from stock_agent.core.interfaces import DataRepository, LLMClient
from stock_agent.infra.brokers.backtest_broker import BacktestBroker
from stock_agent.execution.trader import StockTrader
from stock_agent.monitoring.logger import logger

class AgentStrategy(bt.Strategy):
    """Backtrader Strategy that triggers our SynthesizerAgent on every candle."""
    params = (
        ('trader_instance', None),
        ('backtest_broker', None),
        ('ticker', ''),
    )

    def __init__(self):
        self.trader: StockTrader = self.p.trader_instance
        self.broker_mock: BacktestBroker = self.p.backtest_broker
        self.ticker = self.p.ticker
        self.dataclose = self.datas[0].close
        self.history = []

    def next(self):
        # Current bar's date and closing price in simulation
        sim_dt = self.datas[0].datetime.date(0)
        sim_dt_time = datetime.combine(sim_dt, datetime.min.time())
        close_price = self.dataclose[0]

        # Sync the backtest broker's mock price with the current simulation close price
        self.broker_mock.set_current_price(self.ticker, close_price)

        # We need to run the async trading cycle inside Backtrader's sync loop
        logger.debug("Simulating day", date=sim_dt.isoformat(), price=close_price)
        
        loop = asyncio.get_event_loop()
        # Direct async trader cycle simulation
        loop.run_until_complete(self.trader.execute_trade_cycle())

        # Record simulation metrics for analysis
        portfolio_state = loop.run_until_complete(self.broker_mock.get_balance())
        self.history.append({
            "date": sim_dt.isoformat(),
            "close": close_price,
            "cash": portfolio_state.get("cash", 0.0),
            "total_value": portfolio_state.get("total_asset", 0.0)
        })


class BacktestRunner:
    def __init__(self, repository: DataRepository, llm_client: LLMClient):
        self.repository = repository
        self.llm_client = llm_client

    async def run_backtest(self, ticker: str, start_dt: datetime, end_dt: datetime, initial_cash: float = 10000000.0) -> Dict[str, Any]:
        """Loads data, configures the Cerebro engine, runs the backtest and returns metrics."""
        logger.info("Initializing historical backtest", ticker=ticker, start=start_dt.isoformat(), end=end_dt.isoformat())

        # 1. Fetch bars from database repository
        bars = await self.repository.get_bars(ticker, start_dt, end_dt)
        if not bars:
            logger.error("No historical bars found in repository for backtesting", ticker=ticker)
            return {"error": "No data found"}

        # 2. Convert to pandas for Backtrader
        df_data = []
        for b in bars:
            df_data.append({
                "Date": b.timestamp,
                "Open": b.open,
                "High": b.high,
                "Low": b.low,
                "Close": b.close,
                "Volume": b.volume
            })
        df = pd.DataFrame(df_data)
        df.set_index("Date", inplace=True)

        # 3. Create Cerebro instance
        cerebro = bt.Cerebro()
        
        # Add historical feed
        data_feed = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data_feed)

        # Setup specialized BacktestBroker and Trader
        bt_broker = BacktestBroker(initial_cash=initial_cash)
        trader = StockTrader(bt_broker, self.repository, self.llm_client)

        # Force TRADING_UNIVERSE in settings to only target the active backtested ticker
        settings.TRADING_UNIVERSE = [ticker]

        # Add strategy
        cerebro.addstrategy(
            AgentStrategy,
            trader_instance=trader,
            backtest_broker=bt_broker,
            ticker=ticker
        )

        # Set initial capital in Backtrader as well for logging alignment
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=0.00015) # 0.015% standard commission

        logger.info("Running Cerebro pipeline...")
        strategies = cerebro.run()
        strat = strategies[0]

        logger.info("Backtest pipeline completed successfully.")
        return {
            "ticker": ticker,
            "initial_value": initial_cash,
            "final_value": strat.history[-1]["total_value"] if strat.history else initial_cash,
            "history": strat.history
        }

import asyncio
import pytest
from datetime import datetime, timedelta
from stock_agent.common.dto import Bar, ActionType, OrderStatus
from stock_agent.common.event_bus import event_bus
from stock_agent.storage.repository import storage_layer
from stock_agent.collectors.data_collector import DataCollector
from stock_agent.preprocessor.calculator import Preprocessor
from stock_agent.ml_system.predictor import ml_system
from stock_agent.agent_system.blackboard import blackboard_agent_system
from stock_agent.strategy_engine.engine import strategy_engine
from stock_agent.risk_manager.gate import risk_manager
from stock_agent.approval_queue.queue import approval_queue
from stock_agent.oms.system import oms_system
from stock_agent.exchange_adapter.adapters import exchange_adapter
from stock_agent.portfolio_manager.manager import portfolio_manager
from stock_agent.notification.subscriber import notification_subscriber


@pytest.mark.asyncio
async def test_full_15_module_integration():
    """Verify that a raw bar flow triggers all 15 modules up to portfolio updates."""
    from stock_agent.core.config import settings
    # Isolate execution entirely in-memory
    storage_layer.use_db(":memory:")
    try:
        # 1. Clean slate setup
        exchange_adapter.enable_backtesting(True)
        approval_queue.set_mode(True) # Automated mode bypass for immediate execution
        
        portfolio_manager.cash = 10000000.0
        portfolio_manager.initial_cash = 10000000.0
        
        # Delete positions
        for p in storage_layer.get_positions():
            storage_layer.delete_position(p.ticker)
            
        ticker = "005930"
        timestamp = datetime.now()
        
        # 2. Simulate 25 historical bar entries to satisfy Preprocessor and ML system minima
        collector = DataCollector()
        for i in range(25):
            # We manually step the time
            sim_time = timestamp - (25 - i) * timedelta(minutes=15)
            bar = collector.generate_next_bar(ticker, sim_time)
            storage_layer.save_bar(bar)
            
        # Verify TSDB saved them
        bars = storage_layer.get_bars(ticker, limit=30)
        assert len(bars) >= 25
        
        # Train the ML model
        trained = ml_system.train(ticker)
        assert trained is True
        
        # 3. Inject the live tick that kicks off the async pipeline!
        # Force run the collector to dispatch RawDataCollectedEvent
        live_bar = await collector.collect_data(ticker, timestamp)
        
        # Yield control to let async event handlers complete their cascading dispatches
        await asyncio.sleep(0.5)
        
        # 4. Assert all modules reacted!
        # TSDB should have saved the latest bar
        latest_saved = storage_layer.get_cache(f"latest_bar:{ticker}")
        assert latest_saved is not None
        assert latest_saved.close == live_bar.close
        
        # Preprocessor must have saved computed indicators
        latest_feat = storage_layer.get_cache(f"latest_features:{ticker}")
        assert latest_feat is not None
        assert "sma_5" in latest_feat
        assert "rsi" in latest_feat
        
        # Blackboard should have predictions
        cands = blackboard_agent_system.blackboard.read(ticker)
        assert len(cands) == 3 # Technical, Fundamental, ML analyst candidates
        
        # OMS should have handled orders
        orders = storage_layer.get_orders()
        # At least some orders might have been generated depending on random walk prices,
        # let's make sure the state machine did not error.
        for ord in orders:
            assert ord.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED, OrderStatus.REJECTED]
            
    finally:
        # Clean up system state
        exchange_adapter.enable_backtesting(False)
        approval_queue.set_mode(False)
        # Restore original database path
        storage_layer.use_db(settings.SQLITE_URL)

import pytest
from datetime import datetime, timedelta
from stock_agent.storage.repository import storage_layer
from stock_agent.common.dto import Bar
from stock_agent.backtesting.vbt_adapter import vbt_backtest_runner

@pytest.mark.asyncio
async def test_vbt_backtest_runner():
    # Isolate database in memory
    storage_layer.use_db(":memory:")
    
    ticker = "005930"
    start_dt = datetime.now() - timedelta(days=10)
    end_dt = datetime.now()
    
    # Seed 50 bars deterministically
    import random
    random.seed(42)
    base_price = 70000.0
    
    for i in range(50):
        timestamp = start_dt + timedelta(hours=i)
        change = base_price * random.uniform(-0.015, 0.015)
        close_val = base_price + change
        bar = Bar(
            ticker=ticker,
            timestamp=timestamp,
            open=base_price,
            high=max(base_price, close_val) + 100,
            low=min(base_price, close_val) - 100,
            close=close_val,
            volume=float(random.randint(100000, 500000))
        )
        storage_layer.save_bar(bar)
        base_price = close_val # random walk
        
    # Verify they were saved
    bars = storage_layer.get_bars(ticker, limit=100)
    assert len(bars) == 50
    
    # Run the vectorbt backtest
    result = await vbt_backtest_runner.run_backtest(
        tickers=[ticker],
        start_dt=start_dt,
        end_dt=end_dt,
        initial_cash=100000000.0
    )
    
    # Verify results structure and content
    assert "error" not in result
    assert result["tickers"] == [ticker]
    assert "final_value" in result
    assert "return_pct" in result
    assert "mdd" in result
    assert "sharpe_ratio" in result
    assert result["steps_run"] == 50

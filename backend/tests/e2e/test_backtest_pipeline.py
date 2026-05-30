import pytest
import asyncio
from datetime import datetime, timedelta
from stock_agent.infra.storage.sqlite_repo import SQLiteRepository
from stock_agent.infra.llm.provider import DeepLLMProxy
from stock_agent.backtesting.bt_adapter import BacktestRunner
from stock_agent.backtesting.metrics import calculate_performance_metrics
from stock_agent.core.schemas import Bar

@pytest.mark.asyncio
async def test_full_backtest_pipeline_e2e():
    # Use SQLite in-memory or temporary DB file for testing isolation
    repository = SQLiteRepository(db_url="sqlite:///:memory:")
    llm_client = DeepLLMProxy() # Standard config fallback handles missing key safely
    
    ticker = "005930"
    start_dt = datetime(2026, 1, 1)
    end_dt = datetime(2026, 1, 10)

    # 1. Seed historical dummy price bars
    mock_bars = []
    curr_dt = start_dt
    base_price = 70000.0

    while curr_dt <= end_dt:
        if curr_dt.weekday() < 5:  # Mon to Fri
            mock_bars.append(
                Bar(
                    ticker=ticker,
                    timestamp=curr_dt,
                    open=base_price,
                    high=base_price + 1000.0,
                    low=base_price - 500.0,
                    close=base_price + 200.0,
                    volume=1500000.0
                )
            )
            base_price += 200.0
        curr_dt += timedelta(days=1)

    await repository.save_bars(mock_bars)

    # 2. Instantiate and run BacktestRunner
    runner = BacktestRunner(repository, llm_client)
    result = await runner.run_backtest(ticker, start_dt, end_dt, initial_cash=10000000.0)

    # 3. Assertions
    assert "error" not in result
    assert result["ticker"] == ticker
    assert result["initial_value"] == 10000000.0
    assert len(result["history"]) > 0

    # 4. Assert performance metrics calculate smoothly
    stats = calculate_performance_metrics(result["history"])
    assert stats["initial_portfolio_value"] == 10000000.0
    assert stats["trading_days"] > 0
    assert "max_drawdown_pct" in stats
    assert "sharpe_ratio" in stats

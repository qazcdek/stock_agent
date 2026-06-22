import pytest
import asyncio
from datetime import datetime, timedelta
from stock_agent.infra.storage.sqlite_repo import SQLiteRepository
from stock_agent.backtesting.vbt_adapter import vbt_backtest_runner
from stock_agent.core.schemas import Bar

@pytest.mark.asyncio
async def test_full_backtest_pipeline_e2e():
    # Use SQLite in-memory or temporary DB file for testing isolation
    repository = SQLiteRepository(db_url="sqlite:///:memory:")
    
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

    # 2. Run VBTBacktestRunner
    result = await vbt_backtest_runner.run_backtest(
        tickers=[ticker],
        start_dt=start_dt,
        end_dt=end_dt,
        initial_cash=10000000.0,
        repository=repository
    )

    # 3. Assertions
    assert "error" not in result
    assert result["tickers"] == [ticker]
    assert result["final_value"] > 0
    assert result["return_pct"] is not None
    assert result["mdd"] is not None
    assert result["sharpe_ratio"] is not None

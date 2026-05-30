import asyncio
from datetime import datetime, timedelta
from stock_agent.common.logger import logger
from stock_agent.backtest_engine.runner import backtest_engine

# Trigger imports to register event handlers on the event bus
import stock_agent.preprocessor
import stock_agent.ml_system
import stock_agent.agent_system
import stock_agent.strategy_engine
import stock_agent.risk_manager
import stock_agent.approval_queue
import stock_agent.oms
import stock_agent.exchange_adapter
import stock_agent.portfolio_manager
import stock_agent.notification


async def run_simulation():
    tickers = ["005930", "035720", "BTC"]
    
    # 2 days simulation with 15-minute interval ticks for fast-forward verification
    end_time = datetime.now()
    start_time = end_time - timedelta(days=2)
    
    logger.info("Initializing fast-forward backtesting system simulation...")
    
    metrics = await backtest_engine.run(
        tickers=tickers,
        start_time=start_time,
        end_time=end_time,
        step_minutes=15
    )
    
    print("\n" + "="*50)
    print("      🏆 BACKTEST ENGINE SIMULATION REPORT 🏆      ")
    print("="*50)
    print(f"Target Assets     : {', '.join(metrics['tickers'])}")
    print(f"Simulation Period : {metrics['start_time']} ~ {metrics['end_time']}")
    print(f"Total Steps Run   : {metrics['steps_run']} historical ticks")
    print(f"Final Value       : ₩{metrics['final_value']:,.2f}")
    print(f"Net Return        : {metrics['return_pct']}%")
    print(f"Max Drawdown (MDD): {metrics['mdd']}%")
    print(f"Sharpe Ratio      : {metrics['sharpe_ratio']}")
    print("="*50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_simulation())

import asyncio
import argparse
from datetime import datetime, date
from stock_agent.infra.storage.sqlite_repo import SQLiteRepository
from stock_agent.infra.llm.openai_client import OpenAIClient
from stock_agent.backtesting.bt_adapter import BacktestRunner
from stock_agent.backtesting.metrics import calculate_performance_metrics
from stock_agent.core.schemas import Bar
from stock_agent.monitoring.logger import logger

async def main():
    parser = argparse.ArgumentParser(description="Stock Agent Historical Backtesting CLI tool")
    parser.add_argument("--ticker", type=str, default="005930", help="Ticker code to backtest (e.g. 005930)")
    parser.add_argument("--start", type=str, default="2026-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2026-05-26", help="End date (YYYY-MM-DD)")
    parser.add_argument("--cash", type=float, default=10000000.0, help="Initial simulation cash in KRW")
    
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d")
    end_dt = datetime.strptime(args.end, "%Y-%m-%d")

    logger.info("Initializing Backtest CLI Environment...")
    
    repository = SQLiteRepository()
    llm_client = OpenAIClient() # Automatically utilizes settings fallback

    # Check if there is data in DB, if not, seed some dummy bars for the backtest
    # This prevents dry runs from failing due to empty database tables
    bars = await repository.get_bars(args.ticker, start_dt, end_dt)
    if not bars:
        logger.info("No historical bars found in SQLite. Seeding mock prices for backtest execution...")
        mock_bars = []
        base_price = 72000.0
        # Generate 30 days of mock rising/fluctuating prices
        curr_dt = start_dt
        import random
        random.seed(42)
        
        while curr_dt <= end_dt:
            if curr_dt.weekday() < 5: # Monday to Friday
                change = base_price * random.uniform(-0.02, 0.03)
                open_p = base_price
                close_p = base_price + change
                high_p = max(open_p, close_p) + (base_price * random.uniform(0.001, 0.01))
                low_p = min(open_p, close_p) - (base_price * random.uniform(0.001, 0.01))
                
                mock_bars.append(
                    Bar(
                        ticker=args.ticker,
                        timestamp=curr_dt,
                        open=open_p,
                        high=high_p,
                        low=low_p,
                        close=close_p,
                        volume=random.uniform(500000, 2000000)
                    )
                )
                base_price = close_p
            curr_dt += asyncio.to_thread(lambda: datetime.timedelta(days=1))()
            
        await repository.save_bars(mock_bars)
        logger.info("Successfully seeded mock bars.", count=len(mock_bars))

    runner = BacktestRunner(repository, llm_client)
    result = await runner.run_backtest(args.ticker, start_dt, end_dt, initial_cash=args.cash)

    if "error" in result:
        print(f"Backtest error occurred: {result['error']}")
        return

    # Calculate metrics
    stats = calculate_performance_metrics(result["history"])

    # Pretty Print metrics
    print("\n" + "=" * 55)
    print(f"      📈 BACKTEST PERFORMANCE REPORT: {args.ticker}     ")
    print("=" * 55)
    print(f" 분석 기간     : {args.start} ~ {args.end}")
    print(f" 거래 일수     : {stats['trading_days']} 일")
    print(f" 초기 예수금   : {stats['initial_portfolio_value']:,.0f} 원")
    print(f" 최종 평가금액 : {stats['final_portfolio_value']:,.0f} 원")
    print(f" 누적 수익률   : {stats['total_return_pct']:.2f} %")
    print(f" 샤프 지수     : {stats['sharpe_ratio']:.4f}")
    print(f" 소르티노 지수 : {stats['sortino_ratio']:.4f}")
    print(f" 최대 낙폭(MDD): {stats['max_drawdown_pct']:.2f} %")
    print(f" 일별 승률     : {stats['win_rate_days_pct']:.2f} %")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

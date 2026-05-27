import numpy as np
import pandas as pd
from typing import Dict, Any, List

def calculate_performance_metrics(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates quantitative performance stats (returns, Sharpe, MDD) from portfolio history."""
    if not history:
        return {"error": "History data is empty"}

    df = pd.DataFrame(history)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # 1. Total Cumulative Return
    initial_val = float(df['total_value'].iloc[0])
    final_val = float(df['total_value'].iloc[-1])
    total_return = (final_val - initial_val) / initial_val

    # 2. Daily Returns
    df['daily_return'] = df['total_value'].pct_change().fillna(0.0)
    
    # 3. Sharpe Ratio (assuming risk-free rate is 0.0 for simplicity, annualized 252 trading days)
    mean_return = df['daily_return'].mean()
    std_return = df['daily_return'].std()
    
    if std_return > 0:
        sharpe = (mean_return / std_return) * np.sqrt(252)
    else:
        sharpe = 0.0

    # 4. Sortino Ratio (downside risk only)
    downside_returns = df['daily_return'][df['daily_return'] < 0]
    std_downside = downside_returns.std()
    
    if std_downside > 0:
        sortino = (mean_return / std_downside) * np.sqrt(252)
    else:
        sortino = 0.0

    # 5. Maximum Drawdown (MDD)
    df['peak'] = df['total_value'].cummax()
    df['drawdown'] = (df['total_value'] - df['peak']) / df['peak']
    mdd = float(df['drawdown'].min())

    # 6. Basic stats
    win_days = len(df[df['daily_return'] > 0])
    loss_days = len(df[df['daily_return'] < 0])
    win_ratio = win_days / (win_days + loss_days + 1e-9)

    return {
        "initial_portfolio_value": initial_val,
        "final_portfolio_value": final_val,
        "total_return_pct": total_return * 100.0,
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "max_drawdown_pct": mdd * 100.0,
        "win_rate_days_pct": win_ratio * 100.0,
        "trading_days": len(df)
    }

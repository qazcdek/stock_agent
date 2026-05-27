import pytest
from datetime import datetime
from stock_agent.core.schemas import Order, PortfolioState, Position
from stock_agent.core.enums import Action, OrderType, OrderStatus
from stock_agent.execution.risk_gate import RiskGate

def test_risk_gate_cash_limit():
    gate = RiskGate()
    
    # Portfolio with 10,000 KRW cash
    portfolio = PortfolioState(
        cash=10000.0,
        total_asset=10000.0,
        positions={},
        timestamp=datetime.utcnow()
    )

    # Order demanding 15,000 KRW
    order = Order(
        order_id="test_1",
        ticker="005930",
        action=Action.BUY,
        order_type=OrderType.MARKET,
        quantity=1,
        price=15000.0,
        status=OrderStatus.PENDING,
        created_at=datetime.utcnow()
    )

    passed, reason = gate.validate_order(order, portfolio, daily_traded_amount=0.0)
    assert passed is False
    assert "Cash restriction" in reason


def test_risk_gate_daily_aggregate_breach():
    gate = RiskGate()
    
    # Portfolio with enough cash
    portfolio = PortfolioState(
        cash=10000000.0,
        total_asset=10000000.0,
        positions={},
        timestamp=datetime.utcnow()
    )

    # Order demanding 1,000,000 KRW
    order = Order(
        order_id="test_2",
        ticker="005930",
        action=Action.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
        price=100000.0,
        status=OrderStatus.PENDING,
        created_at=datetime.utcnow()
    )

    # Assume we already traded 4,500,000 KRW today. Adding 1,000,000 KRW exceeds MAX_DAILY_ORDER_AMOUNT (5,000,000 KRW)
    passed, reason = gate.validate_order(order, portfolio, daily_traded_amount=4500000.0)
    assert passed is False
    assert "Daily aggregate limit breach" in reason

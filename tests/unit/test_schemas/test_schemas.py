import pytest
from datetime import datetime
from stock_agent.core.schemas import Signal, Bar
from stock_agent.core.enums import Action

def test_bar_schema_validation():
    # Valid bar should initialize smoothly
    bar = Bar(
        ticker="005930",
        timestamp=datetime.utcnow(),
        open=72000.0,
        high=73500.0,
        low=71500.0,
        close=73000.0,
        volume=1000000.0
    )
    assert bar.ticker == "005930"
    assert bar.close == 73000.0


def test_signal_confidence_boundaries():
    # Valid confidence 0.8
    sig = Signal(
        ticker="000660",
        action=Action.BUY,
        confidence=0.8,
        rationale="Strong indicators support buying.",
        timestamp=datetime.utcnow()
    )
    assert sig.confidence == 0.8

    # Invalid confidence greater than 1.0 should raise ValueError
    with pytest.raises(ValueError):
        Signal(
            ticker="000660",
            action=Action.BUY,
            confidence=1.5,
            rationale="Too confident",
            timestamp=datetime.utcnow()
        )

    # Invalid confidence lower than 0.0 should raise ValueError
    with pytest.raises(ValueError):
        Signal(
            ticker="000660",
            action=Action.BUY,
            confidence=-0.1,
            rationale="Negative confidence",
            timestamp=datetime.utcnow()
        )

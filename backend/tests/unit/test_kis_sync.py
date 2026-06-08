import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from stock_agent.portfolio_manager.manager import PortfolioManager
from stock_agent.storage.repository import storage_layer
from stock_agent.core.schemas import Position as CorePosition


@pytest.mark.asyncio
async def test_portfolio_manager_kis_sync():
    """Verify that PortfolioManager successfully pulls cash and positions from KIS broker when active."""
    # 1. Setup isolated in-memory DB
    storage_layer.use_db(":memory:")
    
    # 2. Instantiate local PortfolioManager
    manager = PortfolioManager(initial_cash=500000000.0)
    
    # Pre-populate SQLite DB with a stale position to test deletion/cleanup
    from stock_agent.common.dto import Position as DtoPosition
    stale_pos = DtoPosition(
        ticker="035420",
        quantity=50,
        avg_price=180000.0,
        current_price=180000.0,
        floating_pnl=0.0
    )
    storage_layer.save_position(stale_pos)
    assert len(storage_layer.get_positions()) == 1

    # 3. Create mock KISBroker instance
    mock_kis = AsyncMock()
    mock_kis.is_mock_mode = False  # Simulate active API mode
    mock_kis.get_balance.return_value = {
        "cash": 74300000.0,
        "total_asset": 124300000.0
    }
    mock_kis.get_positions.return_value = {
        "005930": CorePosition(
            ticker="005930",
            quantity=100,
            avg_price=72000.0,
            current_price=75000.0,
            pnl=300000.0,
            pnl_pct=0.0416
        )
    }

    # 4. Patch KISBroker instantiation to return our mock
    with patch("stock_agent.infra.brokers.kis_broker.KISBroker", return_value=mock_kis):
        await manager.sync_with_kis()
        
        # 5. Assert cash is synced
        assert manager.cash == 74300000.0
        
        # 6. Assert positions in SQLite are updated to match KISBroker returned ones
        db_positions = storage_layer.get_positions()
        # "035420" (stale) should be deleted, "005930" (new from KIS) should be added
        assert len(db_positions) == 1
        assert db_positions[0].ticker == "005930"
        assert db_positions[0].quantity == 100
        assert db_positions[0].avg_price == 72000.0
        assert db_positions[0].current_price == 75000.0
        assert db_positions[0].floating_pnl == 300000.0
        
    # Clean up DB
    storage_layer.use_db("stock_agent.db")

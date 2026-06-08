import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from stock_agent.common.dto import Bar, ActionType
from stock_agent.storage.repository import storage_layer
from stock_agent.agent_system.trading_team import trading_team_system


@pytest.mark.asyncio
async def test_blackboard_trading_team_pipeline():
    """Verify that the full Blackboard Trading Team analysis workflow runs successfully."""
    # 1. Isolate database to in-memory SQLite
    storage_layer.use_db(":memory:")
    
    ticker = "005930"
    now = datetime.now()
    
    # 2. Seed 35 dummy historical bars for TechnicalAnalyst & RiskManagementAgent
    for i in range(35):
        sim_time = now - timedelta(days=35-i)
        # We simulate a steady uptrend to trigger buying signal indicators
        close_price = 70000.0 + (i * 200.0)
        bar = Bar(
            ticker=ticker,
            timestamp=sim_time,
            open=close_price - 100.0,
            high=close_price + 300.0,
            low=close_price - 200.0,
            close=close_price,
            volume=50000 + (i * 1000)
        )
        storage_layer.save_bar(bar)
        
    # Verify bars are saved
    bars = storage_layer.get_bars(ticker, limit=60)
    assert len(bars) == 35

    # 3. Mock the DeepLLMProxy.generate_completion call to prevent actual network calls
    mock_llm_response = (
        '{\n'
        '  "action": "BUY",\n'
        '  "confidence": 0.88,\n'
        '  "rationale": "MACD golden cross confirmed and strong semiconductor export data provides fundamental backing."\n'
        '}'
    )
    
    with patch("stock_agent.infra.llm.provider.DeepLLMProxy.generate_completion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_llm_response
        
        # 4. Run Blackboard analysis
        result = await trading_team_system.run_analysis(ticker)
        
        # 5. Assertions on the final coordinated result
        assert result["ticker"] == ticker
        assert result["action"] == "BUY"
        assert result["confidence"] > 0.5
        assert "Risk Assessment" in result["rationale"]
        
        # Check blackboard state details
        bb_state = result["blackboard_state"]
        
        # Ensure the mock LLM rationale is in the TraderAgent's blackboard state
        trader_state = next(s for s in bb_state if s["source_agent"] == "TraderAgent")
        assert "semiconductor export" in trader_state["reason"]
        # Ensure all 8 agents generated decisions in the blackboard state
        agents = [s["source_agent"] for s in bb_state]
        expected_agents = [
            "TechnicalAnalyst",
            "FundamentalsAnalyst",
            "SentimentAnalyst",
            "NewsAnalyst",
            "BullishResearcher",
            "BearishResearcher",
            "TraderAgent",
            "RiskManagementAgent"
        ]
        for agent in expected_agents:
            assert agent in agents
            
        # Ensure individual agent data was formatted correctly
        tech_state = next(s for s in bb_state if s["source_agent"] == "TechnicalAnalyst")
        assert tech_state["ticker"] == ticker
        assert tech_state["action"] in ["BUY", "SELL", "HOLD"]
        assert 0.0 <= tech_state["weight"] <= 1.0
        assert len(tech_state["reason"]) > 0
        
        # RiskManagementAgent state check
        risk_state = next(s for s in bb_state if s["source_agent"] == "RiskManagementAgent")
        assert risk_state["action"] == "BUY" # Since risk is low and trader decided BUY
        assert "Risk Assessment" in risk_state["reason"]
        
    # Clean up database
    storage_layer.use_db("stock_agent.db")

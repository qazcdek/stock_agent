import pytest
from datetime import date, datetime, timezone
import httpx
from stock_agent.collectors.fundamental_collector import FundamentalCollector
from stock_agent.collectors.price_collector import PriceCollector
from stock_agent.collectors.news_collector import NewsCollector
from stock_agent.core.config import settings
from stock_agent.storage.repository import storage_layer

@pytest.mark.asyncio
async def test_fmp_fundamental_metrics_mock(monkeypatch):
    # Set FMP API key
    monkeypatch.setattr(settings, "FMP_API_KEY", "mock_fmp_key")

    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return [
                {
                    "bookValuePerShareTTM": 55000.0,
                    "peRatioTTM": 12.0,
                    "pbRatioTTM": 1.5,
                    "netIncomePerShareTTM": 6000.0,
                    "dividendYieldPercentageTTM": 2.5,
                    "dividendPerShareTTM": 1500.0
                }
            ]

    async def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = FundamentalCollector()
    metrics = await collector.fetch_fundamental_metrics("005930", date.today())
    
    assert metrics is not None
    assert metrics["ticker"] == "005930"
    assert metrics["bps"] == 55000.0
    assert metrics["per"] == 12.0
    assert metrics["pbr"] == 1.5
    assert metrics["eps"] == 6000.0
    assert metrics["div_yield"] == 2.5
    assert metrics["dps"] == 1500.0


@pytest.mark.asyncio
async def test_fmp_price_bars_mock(monkeypatch):
    monkeypatch.setattr(settings, "FMP_API_KEY", "mock_fmp_key")

    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "symbol": "005930.KS",
                "historical": [
                    {
                        "date": "2026-05-29",
                        "open": 70000.0,
                        "high": 71000.0,
                        "low": 69500.0,
                        "close": 70500.0,
                        "volume": 12000000.0
                    }
                ]
            }

    async def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    storage_layer.use_db(":memory:")
    collector = PriceCollector(storage_layer)
    bars = await collector._fetch_from_fmp("005930", date(2026, 5, 29), date(2026, 5, 29))
    
    assert len(bars) == 1
    assert bars[0].ticker == "005930"
    assert bars[0].open == 70000.0
    assert bars[0].high == 71000.0
    assert bars[0].low == 69500.0
    assert bars[0].close == 70500.0
    assert bars[0].volume == 12000000.0


@pytest.mark.asyncio
async def test_fmp_news_mock(monkeypatch):
    monkeypatch.setattr(settings, "FMP_API_KEY", "mock_fmp_key")

    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return [
                {
                    "title": "Nvidia continuous rally boosts index",
                    "url": "https://fmp.com/nvidia_rally",
                    "text": "Nvidia reaches record high after earnings beat.",
                    "site": "Bloomberg",
                    "symbol": "NVDA",
                    "publishedDate": "2026-05-30 08:30:00"
                }
            ]

    async def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = NewsCollector()
    news = await collector._fetch_fmp_news()
    
    assert len(news) == 1
    assert news[0].title == "Nvidia continuous rally boosts index"
    assert news[0].url == "https://fmp.com/nvidia_rally"
    assert news[0].summary == "Nvidia reaches record high after earnings beat."
    assert news[0].source == "FMP (Bloomberg)"
    assert news[0].ticker == "NASDAQ:NVDA"
    assert news[0].published_at.hour == 8
    assert news[0].published_at.minute == 30

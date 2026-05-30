import pytest
from datetime import datetime, timezone
from stock_agent.collectors.news_collector import NewsCollector, parse_rss_pubdate
from stock_agent.storage.repository import storage_layer
from stock_agent.common.dto import NewsArticle


def test_parse_rss_pubdate():
    # Test correct RFC 822 parsing
    dt = parse_rss_pubdate("Wed, 28 May 2026 12:34:56 GMT")
    assert dt.year == 2026
    assert dt.month == 5
    assert dt.day == 28
    assert dt.hour == 12
    assert dt.minute == 34
    assert dt.second == 56
    assert dt.tzinfo == timezone.utc

    # Test malformed parsing fallback to current time
    dt_fallback = parse_rss_pubdate("invalid date string")
    assert isinstance(dt_fallback, datetime)
    assert dt_fallback.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_news_collector_collection():
    # Isolate storage in memory
    storage_layer.use_db(":memory:")
    
    collector = NewsCollector()
    
    # 1. Run collection
    articles = await collector.collect_general_news()
    
    # Assert we collected some articles (at least the mock fallback articles must be loaded)
    assert len(articles) > 0
    
    # Verify the contents are standardized NewsArticle models
    for art in articles:
        assert isinstance(art, NewsArticle)
        assert art.url != ""
        assert art.title != ""
        assert art.summary != ""
        assert art.source != ""
        assert isinstance(art.published_at, datetime)
        assert art.category in ("finance_economics", "cryptocurrency")
        
    # 2. Verify that they are saved in SQLite StorageLayer
    saved_articles = storage_layer.get_latest_news(limit=50)
    assert len(saved_articles) > 0
    
    # Confirm urls match
    collected_urls = {a.url for a in articles}
    saved_urls = {a.url for a in saved_articles}
    assert saved_urls.issubset(collected_urls)


@pytest.mark.asyncio
async def test_collect_naver_news_live_parsing(monkeypatch):
    from stock_agent.core.config import settings
    # Temporarily set credentials
    monkeypatch.setattr(settings, "NAVER_CLIENT_ID", "test_id")
    monkeypatch.setattr(settings, "NAVER_CLIENT_SECRET", "test_secret")

    # Mock httpx response
    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "items": [
                    {
                        "title": "<b>삼성전자</b> &quot;최신 AI 칩 수주 성공&quot;",
                        "link": "https://news.naver.com/real_news_1",
                        "description": "삼성전자가 인공지능(AI) 분야에서 <b>새로운 돌파구</b>를 마련했습니다.",
                        "pubDate": "Wed, 28 May 2026 12:34:56 +0900"
                    }
                ]
            }

    async def mock_get(*args, **kwargs):
        return MockResponse()

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = NewsCollector()
    news = await collector.collect_naver_news("005930")
    
    assert len(news) == 1
    assert news[0]["ticker"] == "005930"
    assert news[0]["title"] == '삼성전자 "최신 AI 칩 수주 성공"'
    assert news[0]["summary"] == "삼성전자가 인공지능(AI) 분야에서 새로운 돌파구를 마련했습니다."
    assert news[0]["url"] == "https://news.naver.com/real_news_1"
    assert "2026-05-28" in news[0]["published_at"]


@pytest.mark.asyncio
async def test_collect_dart_disclosures_live_parsing(monkeypatch):
    from stock_agent.core.config import settings
    # Temporarily set credentials
    monkeypatch.setattr(settings, "DART_API_KEY", "test_dart_key")

    # Mock httpx response
    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "status": "000",
                "message": "정상",
                "list": [
                    {
                        "corp_code": "00126380",
                        "corp_name": "삼성전자",
                        "stock_code": "005930",
                        "report_nm": "분기보고서 (2026.03)",
                        "rcept_no": "20260515000123",
                        "rcept_dt": "20260515"
                    }
                ]
            }

    async def mock_get(*args, **kwargs):
        return MockResponse()

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    collector = NewsCollector()
    disclosures = await collector.collect_dart_disclosures("005930")
    
    assert len(disclosures) == 1
    assert disclosures[0]["ticker"] == "005930"
    assert disclosures[0]["report_name"] == "분기보고서 (2026.03)"
    assert disclosures[0]["corp_code"] == "00126380"
    assert disclosures[0]["rcept_no"] == "20260515000123"
    assert disclosures[0]["url"] == "http://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515000123"
    assert "2026-05-15" in disclosures[0]["published_at"]


def test_news_category_filter():
    storage_layer.use_db(":memory:")
    
    art1 = NewsArticle(
        url="https://test.com/watchlist_news",
        title="Watchlist Article 1",
        summary="summary 1",
        source="Source A",
        published_at=datetime.now(timezone.utc),
        category="ticker_news",
        ticker="005930"
    )
    
    art2 = NewsArticle(
        url="https://test.com/general_news",
        title="General Article 2",
        summary="summary 2",
        source="Source B",
        published_at=datetime.now(timezone.utc),
        category="finance_economics",
        ticker=None
    )
    
    storage_layer.save_news_article(art1)
    storage_layer.save_news_article(art2)
    
    # 1. Test "all" category
    all_news = storage_layer.get_latest_news(category_filter="all")
    assert len(all_news) == 2
    
    # 2. Test "watchlist" category
    watchlist_news = storage_layer.get_latest_news(category_filter="watchlist")
    assert len(watchlist_news) == 1
    assert watchlist_news[0].url == "https://test.com/watchlist_news"
    
    # 3. Test "general" category
    general_news = storage_layer.get_latest_news(category_filter="general")
    assert len(general_news) == 1
    assert general_news[0].url == "https://test.com/general_news"



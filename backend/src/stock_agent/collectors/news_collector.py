import httpx
import asyncio
import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Any
from stock_agent.core.config import settings
from stock_agent.monitoring.logger import logger
from stock_agent.common.event_bus import event_bus
from stock_agent.common.dto import NewsArticle, RawNewsCollectedEvent
from stock_agent.storage.repository import storage_layer
from stock_agent.infra.storage.multi_db import mongo_manager


def parse_rss_pubdate(pubdate_str: str) -> datetime:
    try:
        dt = email.utils.parsedate_to_datetime(pubdate_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


class NewsCollector:
    def __init__(self):
        pass

    async def collect_general_news(self) -> List[NewsArticle]:
        logger.info("Starting general finance and economics news collection")
        articles: List[NewsArticle] = []

        # 1. Fetch Naver Economy RSS
        try:
            naver_articles = await self._fetch_naver_rss()
            articles.extend(naver_articles)
        except Exception as e:
            logger.warning("Failed to fetch Naver Economy RSS, using offline mock fallback", error=str(e))
            articles.extend(self._get_naver_mock_news())

        # 2. Fetch Google News RSS
        try:
            google_articles = await self._fetch_google_rss()
            articles.extend(google_articles)
        except Exception as e:
            logger.warning("Failed to fetch Google News RSS, using offline mock fallback", error=str(e))
            articles.extend(self._get_google_mock_news())

        # 2b. Fetch Google News Crypto RSS
        try:
            google_crypto_articles = await self._fetch_google_crypto_rss()
            articles.extend(google_crypto_articles)
        except Exception as e:
            logger.warning("Failed to fetch Google News Crypto RSS, using offline mock fallback", error=str(e))
            articles.extend(self._get_google_crypto_mock_news())

        # 3. Fetch Alpha Vantage NEWS_SENTIMENT API
        if settings.ALPHA_VANTAGE_API_KEY:
            try:
                av_articles = await self._fetch_alpha_vantage_news()
                articles.extend(av_articles)
            except Exception as e:
                logger.warning("Failed to fetch Alpha Vantage news, using offline mock fallback", error=str(e))
                articles.extend(self._get_alpha_vantage_mock_news())
        else:
            logger.info("Alpha Vantage API key not set, using default offline mock news")
            articles.extend(self._get_alpha_vantage_mock_news())

        # Standardize and save to database
        saved_count = 0
        for art in articles:
            try:
                # Save to database using mongo_manager
                await mongo_manager.save_news_article(art)
                # Broadcast RawNewsCollectedEvent
                await event_bus.publish(RawNewsCollectedEvent(article=art))
                saved_count += 1
            except Exception as e:
                logger.error("Failed to save or broadcast news article", error=str(e), url=art.url)

        logger.info("Completed general news collection", total_collected=len(articles), saved_and_broadcasted=saved_count)
        return articles

    async def _fetch_naver_rss(self) -> List[NewsArticle]:
        # Using Dong-A Economy RSS as a fully well-formed, live Korean economy RSS feed
        url = "https://rss.donga.com/economy.xml"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            
            root = ET.fromstring(resp.content)
            articles = []
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_date_elem = item.find("pubDate")
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                description = desc_elem.text if desc_elem is not None else ""
                pub_date_str = pub_date_elem.text if pub_date_elem is not None else ""
                
                published_at = parse_rss_pubdate(pub_date_str)
                
                articles.append(NewsArticle(
                    url=link,
                    title=title,
                    summary=description,
                    source="Naver Economy RSS",
                    published_at=published_at,
                    category="finance_economics"
                ))
            return articles

    async def _fetch_google_rss(self) -> List[NewsArticle]:
        url = "https://news.google.com/rss/search?q=finance+AND+economics&hl=en-US&gl=US&ceid=US:en"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            
            root = ET.fromstring(resp.content)
            articles = []
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_date_elem = item.find("pubDate")
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                description = desc_elem.text if desc_elem is not None else ""
                pub_date_str = pub_date_elem.text if pub_date_elem is not None else ""
                
                published_at = parse_rss_pubdate(pub_date_str)
                
                articles.append(NewsArticle(
                    url=link,
                    title=title,
                    summary=description,
                    source="Google News RSS",
                    published_at=published_at,
                    category="finance_economics"
                ))
            return articles

    async def _fetch_google_crypto_rss(self) -> List[NewsArticle]:
        url = "https://news.google.com/rss/search?q=cryptocurrency+AND+blockchain&hl=en-US&gl=US&ceid=US:en"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            
            root = ET.fromstring(resp.content)
            articles = []
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                desc_elem = item.find("description")
                pub_date_elem = item.find("pubDate")
                
                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                description = desc_elem.text if desc_elem is not None else ""
                pub_date_str = pub_date_elem.text if pub_date_elem is not None else ""
                
                published_at = parse_rss_pubdate(pub_date_str)
                
                articles.append(NewsArticle(
                    url=link,
                    title=title,
                    summary=description,
                    source="Google News Crypto RSS",
                    published_at=published_at,
                    category="cryptocurrency"
                ))
            return articles

    def _get_google_crypto_mock_news(self) -> List[NewsArticle]:
        return [
            NewsArticle(
                url="https://news.google.com/mock_crypto_1",
                title="Bitcoin Rally Ignites Global Altcoin Dynamic Market Activity",
                summary="Major digital assets recorded double-digit gains following institutional inflows and positive regulatory signals in multiple regions.",
                source="Google News Crypto RSS (Mock)",
                published_at=datetime.now(timezone.utc),
                category="cryptocurrency"
            ),
            NewsArticle(
                url="https://news.google.com/mock_crypto_2",
                title="Ethereum Layer-2 Networks Witness Unprecedented Transaction Volume Spikes",
                summary="Scalability upgrades and declining gas fees on layer-2 protocols drive decentralized application activity to new historical highs.",
                source="Google News Crypto RSS (Mock)",
                published_at=datetime.now(timezone.utc),
                category="cryptocurrency"
            )
        ]

    async def _fetch_alpha_vantage_news(self) -> List[NewsArticle]:
        api_key = settings.ALPHA_VANTAGE_API_KEY
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&apikey={api_key}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            feed = data.get("feed", [])
            articles = []
            for item in feed:
                title = item.get("title", "")
                url_link = item.get("url", "")
                summary = item.get("summary", "")
                source = item.get("source", "Alpha Vantage")
                
                time_published = item.get("time_published", "")
                try:
                    published_at = datetime.strptime(time_published, "%Y%m%dT%H%M%S")
                    published_at = published_at.replace(tzinfo=timezone.utc)
                except Exception:
                    published_at = datetime.now(timezone.utc)
                
                articles.append(NewsArticle(
                    url=url_link,
                    title=title,
                    summary=summary,
                    source=f"Alpha Vantage ({source})",
                    published_at=published_at,
                    category="finance_economics"
                ))
            return articles

    def _get_naver_mock_news(self) -> List[NewsArticle]:
        return [
            NewsArticle(
                url="https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=101",
                title="[종합] 한국은행 기준금리 3.50%로 연 10회 연속 동결... '성장세 둔화 우려'",
                summary="한국은행 금융통화위원회가 최근 환율 변동성 확대에도 불구하고 내수 진작을 위해 현 기준금리를 동결하기로 결정했습니다.",
                source="Naver Economy RSS (Mock)",
                published_at=datetime.now(timezone.utc),
                category="finance_economics"
            ),
            NewsArticle(
                url="https://finance.naver.com/",
                title="반도체 수출 호조 지속으로 5월 무역수지 40억 달러 흑자... '수출 경기 견조'",
                summary="산업통상자원부에 따르면 5월 수출액이 AI 서버 시장 호황에 힘입어 전년 동기 대비 11.5% 증가하며 무역수지 흑자를 이끌었습니다.",
                source="Naver Economy RSS (Mock)",
                published_at=datetime.now(timezone.utc),
                category="finance_economics"
            )
        ]

    def _get_google_mock_news(self) -> List[NewsArticle]:
        return [
            NewsArticle(
                url="https://news.google.com/mock_finance_1",
                title="Global Inflation Shows Signs of Moderating as Fed Signals Rate Outlook",
                summary="Economic analysts expect the Federal Reserve to consider a soft landing scenario as the core inflation metrics align with forecast paths.",
                source="Google News RSS (Mock)",
                published_at=datetime.now(timezone.utc),
                category="finance_economics"
            ),
            NewsArticle(
                url="https://news.google.com/mock_finance_2",
                title="US Treasury Yields Edge Lower Amid Cooling Macroeconomic Growth Indicators",
                summary="Bond yields slid to their lowest levels in two weeks following a weaker-than-expected retail sales print and cooling factory data.",
                source="Google News RSS (Mock)",
                published_at=datetime.now(timezone.utc),
                category="finance_economics"
            )
        ]

    def _get_alpha_vantage_mock_news(self) -> List[NewsArticle]:
        return [
            NewsArticle(
                url="https://www.alphavantage.co/mock_av_1",
                title="Federal Reserve Open Market Committee Minutes Reveal Concerns Over Long-Term Productivity Rates",
                summary="The central bank officials noted that structural labor constraints and energy cost dynamics might keep medium-term rates slightly elevated.",
                source="Alpha Vantage (Mock)",
                published_at=datetime.now(timezone.utc),
                category="finance_economics"
            )
        ]

    async def collect_naver_news(self, ticker: str, query: str = "주가") -> List[Dict[str, Any]]:
        """Collects news articles related to the ticker using Naver News RSS or mock data if keys are absent."""
        # Standardize query based on asset class (e.g. crypto coins or US symbols should search for "뉴스" instead of "주가")
        if query == "주가":
            if ticker in ("BTC", "ETH", "SOL", "XRP") or not ticker.isdigit():
                query = "뉴스"
                
        logger.info("Collecting news from Naver Search", ticker=ticker, query=query)
        
        client_id = settings.NAVER_CLIENT_ID
        client_secret = settings.NAVER_CLIENT_SECRET

        news_list = []

        if client_id and client_secret and client_id != "your_naver_client_id_here":
            try:
                import re
                import html
                
                # Search for "{ticker} {query}" (e.g. "005930 주가")
                search_query = f"{ticker} {query}"
                url = "https://openapi.naver.com/v1/search/news.json"
                headers = {
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                }
                params = {
                    "query": search_query,
                    "display": 10,
                    "sort": "sim"
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url, headers=headers, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    items = data.get("items", [])
                    for item in items:
                        title = item.get("title", "")
                        link = item.get("link", "")
                        desc = item.get("description", "")
                        pub_date_str = item.get("pubDate", "")
                        
                        # Clean HTML tags and unescape XML/HTML entities
                        clean_title = html.unescape(re.sub(r'<[^>]*>', '', title))
                        clean_desc = html.unescape(re.sub(r'<[^>]*>', '', desc))
                        
                        pub_date_dt = parse_rss_pubdate(pub_date_str)
                        
                        # Construct and persist standard NewsArticle model
                        art = NewsArticle(
                            url=link,
                            title=clean_title,
                            summary=clean_desc,
                            source="Naver News Search",
                            published_at=pub_date_dt,
                            category="ticker_news",
                            ticker=ticker
                        )
                        
                        try:
                            await mongo_manager.save_news_article(art)
                            await event_bus.publish(RawNewsCollectedEvent(article=art))
                        except Exception as e:
                            logger.error("Failed to save or broadcast live Naver search news article", error=str(e), url=link)

                        news_list.append({
                            "ticker": ticker,
                            "title": clean_title,
                            "summary": clean_desc,
                            "url": link,
                            "published_at": pub_date_dt.isoformat()
                        })
                    if news_list:
                        logger.info("Successfully gathered live news from Naver Search API", ticker=ticker, count=len(news_list))
                        return news_list
            except Exception as e:
                logger.error("Failed to fetch live Naver Search News, falling back to mock", ticker=ticker, error=str(e))

        # Fallback Mock news
        await asyncio.sleep(0.05) # Simulate network latency
        
        mock_items = [
            {
                "title": f"[{ticker}] 2분기 영업이익 전년대비 15% 증가... 시장 예상치 상회 전망",
                "summary": "반도체 및 IT 부문의 견고한 글로벌 수요 덕분에 영업이익이 크게 증가할 것으로 예측됩니다.",
                "url": f"https://news.naver.com/mock_{ticker}_1",
            },
            {
                "title": f"[{ticker}] 글로벌 공급망 불안에 따른 원자재 비용 압박 지속",
                "summary": "최근 거시경제 불확실성과 지정학적 리스크로 원가 부담이 일부 우려되나, 마진 방어가 가능할 것으로 보입니다.",
                "url": f"https://news.naver.com/mock_{ticker}_2",
            },
            {
                "title": f"[{ticker}] AI 혁신 기술 투자 대폭 확대 발표",
                "summary": "미래 성장 동력 확보를 위해 대규모 차세대 인공지능 연구소 건립 및 인재 영입을 추진합니다.",
                "url": f"https://news.naver.com/mock_{ticker}_3",
            }
        ]

        news_list = []
        for item in mock_items:
            pub_date_dt = datetime.now(timezone.utc)
            art = NewsArticle(
                url=item["url"],
                title=item["title"],
                summary=item["summary"],
                source="Naver News Search (Mock)",
                published_at=pub_date_dt,
                category="ticker_news",
                ticker=ticker
            )
            
            try:
                await mongo_manager.save_news_article(art)
                await event_bus.publish(RawNewsCollectedEvent(article=art))
            except Exception as e:
                logger.error("Failed to save or broadcast mock Naver Search news article", error=str(e), url=item["url"])

            news_list.append({
                "ticker": ticker,
                "title": item["title"],
                "summary": item["summary"],
                "url": item["url"],
                "published_at": pub_date_dt.isoformat()
            })
        
        logger.info("Successfully gathered mock news articles", ticker=ticker, count=len(news_list))
        return news_list

    async def collect_dart_disclosures(self, ticker: str) -> List[Dict[str, Any]]:
        """Collects official corporate disclosures from Open DART API, falling back to mocks if keys are absent."""
        logger.info("Collecting DART disclosures", ticker=ticker)
        
        api_key = settings.DART_API_KEY
        if api_key and api_key != "your_opendart_api_key_here":
            try:
                # Map KOSPI tickers to exact Open DART 8-digit corporate codes
                TICKER_TO_CORP_CODE = {
                    "005930": "00126380",  # Samsung Electronics
                    "000660": "00164779",  # SK Hynix
                    "035420": "00266961",  # NAVER
                    "035720": "00258865",  # Kakao
                }
                corp_code = TICKER_TO_CORP_CODE.get(ticker)
                
                if corp_code:
                    # Fetch filings from Open DART API
                    # Fetching latest 10 reports over the past 3 months
                    url = "https://opendart.fss.or.kr/api/list.json"
                    params = {
                        "crtfc_key": api_key,
                        "corp_code": corp_code,
                        "page_count": 10
                    }
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                        
                        # Status "000" means normal success
                        if data.get("status") == "000":
                            filings = data.get("list", [])
                            disclosures = []
                            for item in filings:
                                rcept_no = item.get("rcept_no", "")
                                rcept_dt_str = item.get("rcept_dt", "")
                                
                                try:
                                    published_at = datetime.strptime(rcept_dt_str, "%Y%m%d").replace(tzinfo=timezone.utc).isoformat()
                                except Exception:
                                    published_at = datetime.now(timezone.utc).isoformat()
                                    
                                disclosures.append({
                                    "ticker": ticker,
                                    "report_name": item.get("report_nm", ""),
                                    "corp_code": item.get("corp_code", corp_code),
                                    "rcept_no": rcept_no,
                                    "url": f"http://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                                    "published_at": published_at
                                })
                            if disclosures:
                                logger.info("Successfully gathered disclosures from Open DART", ticker=ticker, count=len(disclosures))
                                return disclosures
                        else:
                            logger.warning("Open DART API returned non-success code", status=data.get("status"), message=data.get("message"))
                else:
                    if ticker.isdigit() and len(ticker) == 6:
                        logger.info("Ticker has no mapped DART corporate code. Falling back to mock disclosures.", ticker=ticker)
                    else:
                        logger.info("Ticker is not a Korean stock corporation. Skipping DART collection.", ticker=ticker)
                        return []
            except Exception as e:
                logger.error("Failed to query Open DART disclosures, falling back to mock", ticker=ticker, error=str(e))

        # Fallback Mock disclosures
        await asyncio.sleep(0.05)
        mock_disclosures = [
            {
                "ticker": ticker,
                "report_name": "분기보고서 (2026.03)",
                "corp_code": "00126380",
                "rcept_no": "20260515000123",
                "url": "http://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515000123",
                "published_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "ticker": ticker,
                "report_name": "[기재정정]단일판매ㆍ공급계약체결",
                "corp_code": "00126380",
                "rcept_no": "20260520000456",
                "url": "http://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260520000456",
                "published_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        logger.info("Successfully gathered mock DART disclosures", ticker=ticker, count=len(mock_disclosures))
        return mock_disclosures

import json
from stock_agent.agents.base import Analyst
from stock_agent.core.enums import AgentType
from stock_agent.core.schemas import AgentReport
from stock_agent.core.interfaces import LLMClient
from stock_agent.infra.llm.provider import FastLLMProxy
from stock_agent.collectors.news_collector import NewsCollector
from stock_agent.monitoring.logger import logger

class NewsAnalyst(Analyst):
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or FastLLMProxy()
        self.collector = NewsCollector()

    async def analyze(self, ticker: str) -> AgentReport:
        logger.info("Running news sentiment and disclosure analysis", ticker=ticker)
        
        # Gather articles and disclosures
        articles = await self.collector.collect_naver_news(ticker)
        disclosures = await self.collector.collect_dart_disclosures(ticker)

        if not articles and not disclosures:
            logger.warning("No news or disclosures gathered. Returning neutral news report.", ticker=ticker)
            return AgentReport(
                agent_type=AgentType.NEWS,
                ticker=ticker,
                score=0.0,
                rationale="해당 종목에 대한 최근 7일 내 뉴스 및 공시 정보가 없어 감성 중립 판정을 내립니다."
            )

        # Build context
        context_items = []
        for i, art in enumerate(articles, 1):
            context_items.append(f"[뉴스 {i}] 제목: {art['title']}\n요약: {art['summary']}")
        for i, disc in enumerate(disclosures, 1):
            context_items.append(f"[공시 {i}] 명칭: {disc['report_name']}\n접수번호: {disc['rcept_no']}")
        
        context_str = "\n\n".join(context_items)

        # Attempt to use LLM sentiment analysis
        system_prompt = (
            "당신은 금융 뉴스 및 기업 공시 전문 감성 분석 에이전트입니다. "
            "주어진 기사와 공시 텍스트를 정밀 분석하여 시장 감정을 파악하세요.\n"
            "출력은 반드시 다음 JSON 형식을 만족해야 하며, 다른 여분의 설명 텍스트를 절대 추가하지 마세요.\n"
            "{\n"
            "  \"score\": 0.5,\n"
            "  \"rationale\": \"주요 긍정적 사유 요약 및 감성 판단 근거...\"\n"
            "}\n"
            "score 범위: -1.0 (극도 부정/악재) ~ 1.0 (극도 긍정/호재)."
        )
        
        user_prompt = f"다음은 주식 종목 [{ticker}]에 관한 최근 언론 보도 및 공시 목록입니다.\n\n{context_str}\n\n감성 점수와 근거를 분석해 주세요."

        try:
            # Check if LLM client is fully active
            response_text = await self.llm_client.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            # Clean response text from markdown block wrappers if LLM returned them
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                # Remove the first and last lines
                if len(lines) >= 3:
                    response_text = "\n".join(lines[1:-1])
            
            data = json.loads(response_text)
            score = float(data.get("score", 0.0))
            rationale = data.get("rationale", "LLM 감성 분석이 수행되었습니다.")
            logger.info("LLM News sentiment analysis successful", ticker=ticker, score=score)

        except Exception as e:
            logger.warning("LLM news analysis failed or API key not set. Running fallback rules-based NLP engine.", error=str(e))
            score, rationale = self._rules_based_fallback_analysis(articles, disclosures)
            logger.info("Rules-based news sentiment fallback completed", ticker=ticker, score=score)

        return AgentReport(
            agent_type=AgentType.NEWS,
            ticker=ticker,
            score=score,
            rationale=rationale,
            metadata={
                "article_count": len(articles),
                "disclosure_count": len(disclosures)
            }
        )

    def _rules_based_fallback_analysis(self, articles: list, disclosures: list) -> tuple[float, str]:
        """A robust keywords-matching parser when LLM services are inaccessible."""
        positive_keywords = ["영업이익 증가", "상회", "이익 증가", "투자 확대", "호재", "혁신", "성장", "해소", "체결", "수주"]
        negative_keywords = ["부담", "우려", "리스크", "원가 상승", "감소", "악재", "소송", "손실", "지연", "불안"]

        pos_count = 0
        neg_count = 0
        matched_pos = []
        matched_neg = []

        all_texts = []
        for a in articles:
            all_texts.append(a["title"] + " " + a["summary"])
        for d in disclosures:
            all_texts.append(d["report_name"])

        full_text = " ".join(all_texts)

        for kw in positive_keywords:
            if kw in full_text:
                pos_count += 1
                matched_pos.append(kw)
        for kw in negative_keywords:
            if kw in full_text:
                neg_count += 1
                matched_neg.append(kw)

        # Score generation based on keywords match ratios
        total = pos_count + neg_count
        if total == 0:
            return 0.0, "최근 기사와 공시에서 감성에 큰 영향을 주는 핵심 키워드를 검출하지 못하여 중립을 부여합니다."
        
        raw_score = (pos_count - neg_count) / total
        # Cap score between -0.8 and +0.8 for safety in rules-based approach
        score = max(-0.8, min(0.8, raw_score))

        pos_str = ", ".join(matched_pos)
        neg_str = ", ".join(matched_neg)

        rationale = f"키워드 기반 분석 결과: 긍정 키워드({pos_str if pos_str else '없음'})와 부정 키워드({neg_str if neg_str else '없음'})가 검출되었습니다."
        if score > 0:
            rationale += " 전반적으로 사업 확장 및 실적 개선 기대감이 우세하여 긍정적인 평가를 부여합니다."
        elif score < 0:
            rationale += " 원가 인상 및 글로벌 거시 리스크 우려 등 부정적 헤드라인의 노출도가 높아 보수적인 투자를 제안합니다."
        else:
            rationale += " 긍부정 재료가 팽팽히 맞서고 있어 신중한 접근이 필요합니다."

        return score, rationale

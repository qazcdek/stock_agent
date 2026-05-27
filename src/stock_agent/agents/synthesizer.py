import json
from datetime import datetime
from stock_agent.agents.base import Analyst
from stock_agent.agents.technical import TechnicalAnalyst
from stock_agent.agents.fundamental import FundamentalAnalyst
from stock_agent.agents.news import NewsAnalyst
from stock_agent.core.enums import Action, AgentType
from stock_agent.core.schemas import Signal, AgentReport
from stock_agent.core.interfaces import DataRepository, LLMClient
from stock_agent.monitoring.logger import logger

class SynthesizerAgent:
    def __init__(self, repository: DataRepository, llm_client: LLMClient):
        self.repository = repository
        self.llm_client = llm_client
        self.technical_analyst = TechnicalAnalyst(repository)
        self.fundamental_analyst = FundamentalAnalyst()
        self.news_analyst = NewsAnalyst(llm_client)

    async def generate_trade_signal(self, ticker: str) -> Signal:
        """Invokes all sub-analysts, combines reports, and synthesizes a final high-conviction trade Signal."""
        logger.info("Starting multi-criteria decision synthesis", ticker=ticker)

        # 1. Run all sub-agents concurrently
        reports = []
        try:
            tech_report, fund_report, news_report = await asyncio.gather(
                self.technical_analyst.analyze(ticker),
                self.fundamental_analyst.analyze(ticker),
                self.news_analyst.analyze(ticker)
            )
            reports.extend([tech_report, fund_report, news_report])
        except Exception as e:
            logger.error("Failed during sub-agents execution, running sequential fallback", ticker=ticker, error=str(e))
            # Safe sequential fallback
            tech_report = await self.technical_analyst.analyze(ticker)
            fund_report = await self.fundamental_analyst.analyze(ticker)
            news_report = await self.news_analyst.analyze(ticker)
            reports.extend([tech_report, fund_report, news_report])

        # 2. Build multi-agent reports prompt
        reports_summary = (
            f"[1. 기술적 분석 에이전트]\n점수(범위 -1~1): {tech_report.score}\n분석 사유: {tech_report.rationale}\n\n"
            f"[2. 기본적 분석 에이전트]\n점수(범위 -1~1): {fund_report.score}\n분석 사유: {fund_report.rationale}\n\n"
            f"[3. 뉴스/공시 감성 에이전트]\n점수(범위 -1~1): {news_report.score}\n분석 사유: {news_report.rationale}"
        )

        system_prompt = (
            "당신은 금융 투자 위원회의 수석 포트폴리오 매니저이자 최종 의사결정권자(Synthesizer)입니다. "
            "기술, 기본 재무, 뉴스 감성 에이전트들의 보고서를 정밀 검토하여 최종 투자 신호(BUY, SELL, HOLD)를 결정하세요.\n"
            "출력은 반드시 다음 JSON 형식을 만족해야 하며, 다른 여분의 텍스트를 절대 추가하지 마세요.\n"
            "{\n"
            "  \"action\": \"BUY\",\n"
            "  \"confidence\": 0.85,\n"
            "  \"rationale\": \"각 에이전트 보고서를 조율한 종합 의사결정 사유...\"\n"
            "}\n"
            "action: BUY, SELL, HOLD 중 하나\n"
            "confidence: 0.0 ~ 1.0 (최종 매매 신뢰 수준)"
        )

        user_prompt = f"다음은 주식 종목 [{ticker}]에 대해 수집된 3개 하위 에이전트의 종합 보고서입니다.\n\n{reports_summary}\n\n최종 의사결정을 내려주세요."

        try:
            # Call LLM
            response_text = await self.llm_client.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2
            )

            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if len(lines) >= 3:
                    response_text = "\n".join(lines[1:-1])

            data = json.loads(response_text)
            action = Action(data.get("action", "HOLD").upper())
            confidence = float(data.get("confidence", 0.5))
            rationale = data.get("rationale", "LLM 종합 분석이 성공적으로 실행되었습니다.")
            logger.info("LLM synthesis successfully created signal", ticker=ticker, action=action, confidence=confidence)

        except Exception as e:
            logger.warning("LLM Synthesis failed, running mathematical weighted consensus fallback.", error=str(e))
            action, confidence, rationale = self._weighted_consensus_fallback(tech_report, fund_report, news_report)
            logger.info("Consensus fallback successfully created signal", ticker=ticker, action=action, confidence=confidence)

        signal = Signal(
            ticker=ticker,
            action=action,
            confidence=confidence,
            rationale=rationale,
            timestamp=datetime.utcnow()
        )

        # Save to database for history
        await self.repository.save_signal(signal)
        return signal

    def _weighted_consensus_fallback(self, tech: AgentReport, fund: AgentReport, news: AgentReport) -> tuple[Action, float, str]:
        """A robust weighted calculation of signals when LLM is unavailable."""
        # Technical: 35%, Fundamental: 35%, News Sentiment: 30%
        weighted_score = (tech.score * 0.35) + (fund.score * 0.35) + (news.score * 0.30)
        
        # Decide Action based on threshold rules
        if weighted_score >= 0.25:
            action = Action.BUY
            confidence = min(1.0, 0.5 + abs(weighted_score))
            rationale = (
                f"가중 합산 점수 {weighted_score:.2f}로 긍정 매입 임계값을 넘었습니다. "
                f"기술지표({tech.score:.1f}), 기본재무({fund.score:.1f}), 뉴스감성({news.score:.1f})이 종합 상승 동력을 강하게 지지하여 매수 신호를 도출합니다."
            )
        elif weighted_score <= -0.25:
            action = Action.SELL
            confidence = min(1.0, 0.5 + abs(weighted_score))
            rationale = (
                f"가중 합산 점수 {weighted_score:.2f}로 부정 매도 임계값에 도달했습니다. "
                f"기술지표({tech.score:.1f}), 기본재무({fund.score:.1f}), 뉴스감성({news.score:.1f})에 나타난 불안 요인 및 하락 트렌드로 리스크 방어적 매도를 제안합니다."
            )
        else:
            action = Action.HOLD
            confidence = 1.0 - abs(weighted_score)
            rationale = (
                f"가중 합산 점수 {weighted_score:.2f}로 중립 밴드 내에 위치합니다. "
                "하위 에이전트 간 신호가 엇갈리거나 뚜렷한 모멘텀이 포착되지 않아 대기(HOLD) 스탠스를 유지합니다."
            )

        return action, confidence, rationale
import asyncio # Ensure asyncio is present for gather in synthesis

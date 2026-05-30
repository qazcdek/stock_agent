from datetime import date
from stock_agent.agents.base import Analyst
from stock_agent.core.enums import AgentType
from stock_agent.core.schemas import AgentReport
from stock_agent.collectors.fundamental_collector import FundamentalCollector
from stock_agent.monitoring.logger import logger

class FundamentalAnalyst(Analyst):
    def __init__(self):
        self.collector = FundamentalCollector()

    async def analyze(self, ticker: str) -> AgentReport:
        logger.info("Running fundamental valuation analysis", ticker=ticker)
        
        metrics = await self.collector.fetch_recent_fundamentals(ticker)
        
        if not metrics:
            logger.warning("No valuation metrics available. Returning neutral fundamental report.", ticker=ticker)
            return AgentReport(
                agent_type=AgentType.FUNDAMENTAL,
                ticker=ticker,
                score=0.0,
                rationale="재무 분석 지표 수집에 실패하여 기본적 분석을 건너뛰고 중립 판정을 내립니다."
            )

        per = metrics.get("per", 0.0)
        pbr = metrics.get("pbr", 0.0)
        eps = metrics.get("eps", 0.0)
        div_yield = metrics.get("div_yield", 0.0)

        score = 0.0
        reasons = []

        # 1. Evaluate PER (Price-to-Earnings Ratio)
        if per == 0.0:
            reasons.append("해당 기업은 최근 적자 기록으로 PER 수치 산출이 불가능하여 밸류에이션 할인이 적용됩니다.")
            score -= 0.3
        elif per < 8.0:
            reasons.append(f"PER가 {per:.2f}배 수준으로 동종 업계 평균 및 이익 창출력 대비 극심하게 저평가되어 있습니다.")
            score += 0.5
        elif per < 15.0:
            reasons.append(f"PER가 {per:.2f}배 수준으로 적정 및 안정적인 가격 수준을 나타내고 있습니다.")
            score += 0.2
        elif per > 35.0:
            reasons.append(f"PER가 {per:.2f}배로 성장 기대감이 선반영되어 있거나 밸류에이션 고평가 영역에 속합니다.")
            score -= 0.4
        else:
            reasons.append(f"PER는 {per:.2f}배로 평이한 밸류에이션 영역에 있습니다.")

        # 2. Evaluate PBR (Price-to-Book Ratio)
        if pbr == 0.0:
            pass
        elif pbr < 0.7:
            reasons.append(f"PBR이 {pbr:.2f}배로 장부상 순자산 가치 대비 크게 할인되어 청산가치 수준의 높은 가격 방어력이 기대됩니다.")
            score += 0.3
        elif pbr < 1.5:
            reasons.append(f"PBR이 {pbr:.2f}배로 자산 가치 대비 합리적인 지지선에 위치해 있습니다.")
            score += 0.1
        elif pbr > 4.0:
            reasons.append(f"PBR이 {pbr:.2f}배로 무형자산 가치 혹은 프리미엄이 높게 형성되어 단기 자산 매력도는 다소 낮습니다.")
            score -= 0.2

        # 3. Dividend Yield
        if div_yield > 3.0:
            reasons.append(f"배당수익률이 {div_yield:.2f}%로 주주환원 성향이 강하고 고배당 매력도가 돋보입니다.")
            score += 0.2

        # Bounds checking (-1.0 to 1.0)
        score = max(-1.0, min(1.0, score))
        rationale = " ".join(reasons)

        report = AgentReport(
            agent_type=AgentType.FUNDAMENTAL,
            ticker=ticker,
            score=score,
            rationale=rationale,
            metadata=metrics
        )
        logger.info("Fundamental analysis completed", ticker=ticker, score=score)
        return report

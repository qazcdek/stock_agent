from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from stock_agent.agents.base import Analyst
from stock_agent.core.enums import AgentType
from stock_agent.core.schemas import AgentReport
from stock_agent.core.interfaces import DataRepository
from stock_agent.monitoring.logger import logger

class TechnicalAnalyst(Analyst):
    def __init__(self, repository: DataRepository):
        self.repository = repository

    async def analyze(self, ticker: str) -> AgentReport:
        logger.info("Running technical analysis", ticker=ticker)
        
        # Retrieve recent 60 days of historical bar data to compute indicators
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=90)
        bars = await self.repository.get_bars(ticker, start_dt, end_dt)
        
        if len(bars) < 15:
            logger.warning("Insufficient bar data for indicators. Returning neutral technical report.", ticker=ticker, data_points=len(bars))
            return AgentReport(
                agent_type=AgentType.TECHNICAL,
                ticker=ticker,
                score=0.0,
                rationale="기술 분석을 수행하기 위한 데이터가 부족합니다 (최소 15 영업일 필요)."
            )

        # Convert to pandas DataFrame for quick technical indicators calculation
        df = pd.DataFrame([b.model_dump() for b in bars])
        df = df.sort_values(by="timestamp").reset_index(drop=True)
        
        close = df['close']
        
        # 1. Simple Moving Averages (SMA 5, 20)
        df['sma_5'] = close.rolling(window=5).mean()
        df['sma_20'] = close.rolling(window=20).mean()
        
        # 2. Relative Strength Index (RSI 14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))

        # Latest values
        latest_close = float(close.iloc[-1])
        latest_sma5 = float(df['sma_5'].iloc[-1]) if not pd.isna(df['sma_5'].iloc[-1]) else latest_close
        latest_sma20 = float(df['sma_20'].iloc[-1]) if not pd.isna(df['sma_20'].iloc[-1]) else latest_close
        latest_rsi = float(df['rsi'].iloc[-1]) if not pd.isna(df['rsi'].iloc[-1]) else 50.0

        # Compute Technical Sentiment Score (Range: -1.0 to 1.0)
        score = 0.0
        reasons = []

        # SMA Golden Cross / Death Cross / Trend Assessment
        if latest_sma5 > latest_sma20:
            score += 0.4
            reasons.append("단기 이동평균선(5일)이 장기 이동평균선(20일) 위에 머물며 상승 트렌드를 유지하고 있습니다.")
        else:
            score -= 0.4
            reasons.append("단기 이동평균선(5일)이 장기 이동평균선(20일) 아래에 형성되어 하락 트렌드를 보이고 있습니다.")

        # RSI Overbought/Oversold levels
        if latest_rsi < 30:
            score += 0.5
            reasons.append(f"RSI 수치가 {latest_rsi:.1f}로 과매도(Oversold) 구간에 진입하여 기술적 반등 가능성이 높습니다.")
        elif latest_rsi > 70:
            score -= 0.5
            reasons.append(f"RSI 수치가 {latest_rsi:.1f}로 과매수(Overbought) 구간에 진입하여 단기 차익 실현 압력이 예상됩니다.")
        else:
            reasons.append(f"RSI 수치는 {latest_rsi:.1f}로 중립적인 가격 모멘텀을 나타내고 있습니다.")

        # Price position relative to SMAs
        if latest_close > latest_sma5:
            score += 0.1
        else:
            score -= 0.1

        # Bounds checking (-1.0 to 1.0)
        score = max(-1.0, min(1.0, score))
        rationale = " ".join(reasons)

        report = AgentReport(
            agent_type=AgentType.TECHNICAL,
            ticker=ticker,
            score=score,
            rationale=rationale,
            metadata={
                "latest_close": latest_close,
                "sma_5": latest_sma5,
                "sma_20": latest_sma20,
                "rsi_14": latest_rsi
            }
        )
        logger.info("Technical analysis completed", ticker=ticker, score=score)
        return report

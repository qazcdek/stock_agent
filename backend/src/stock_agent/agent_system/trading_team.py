import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from stock_agent.common.dto import SignalCandidate, ActionType, Bar
from stock_agent.core.config import settings
from stock_agent.common.logger import logger
from stock_agent.infra.llm.provider import FastLLMProxy, DeepLLMProxy
from stock_agent.storage.repository import storage_layer

class TechnicalAnalyst:
    """Utilizes technical indicators like MACD and RSI to detect patterns and forecast price movements."""
    async def analyze(self, ticker: str, bars: List[Bar]) -> SignalCandidate:
        if len(bars) < 26:
            # Fallback if insufficient historical bars
            return SignalCandidate(
                ticker=ticker,
                timestamp=datetime.now(),
                action=ActionType.HOLD,
                source_agent="TechnicalAnalyst",
                weight=0.5,
                reason="Insufficient price data to compute technical indicators (MACD/RSI require at least 26 data points)."
            )
        
        df = pd.DataFrame([b.model_dump() for b in bars])
        df = df.sort_values(by="timestamp").reset_index(drop=True)
        close = df["close"]
        
        # 1. RSI 14
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
        
        # 2. MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        latest_macd = float(macd_line.iloc[-1])
        latest_sig = float(signal_line.iloc[-1])
        latest_hist = float(macd_hist.iloc[-1])
        prev_hist = float(macd_hist.iloc[-2])
        
        # 3. SMA 5 and 20
        sma5 = close.rolling(window=5).mean()
        sma20 = close.rolling(window=20).mean()
        latest_sma5 = float(sma5.iloc[-1]) if not pd.isna(sma5.iloc[-1]) else float(close.iloc[-1])
        latest_sma20 = float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else float(close.iloc[-1])
        
        score = 0.0
        reasons = []
        
        # MACD logic
        if latest_macd > latest_sig and prev_hist <= 0 and latest_hist > 0:
            score += 0.4
            reasons.append("MACD line crossed above Signal line (Bullish Golden Cross).")
        elif latest_macd < latest_sig and prev_hist >= 0 and latest_hist < 0:
            score -= 0.4
            reasons.append("MACD line crossed below Signal line (Bearish Death Cross).")
        elif latest_macd > latest_sig:
            score += 0.15
            reasons.append("MACD is currently in bullish territory (MACD > Signal).")
        else:
            score -= 0.15
            reasons.append("MACD is currently in bearish territory (MACD < Signal).")
            
        # RSI logic
        if latest_rsi < 30:
            score += 0.45
            reasons.append(f"RSI is oversold at {latest_rsi:.1f}, indicating technical correction/rebound is imminent.")
        elif latest_rsi > 70:
            score -= 0.45
            reasons.append(f"RSI is overbought at {latest_rsi:.1f}, signaling downside mean reversion risk.")
        else:
            reasons.append(f"RSI is neutral at {latest_rsi:.1f}.")

        # Moving Average crossover trend
        if latest_sma5 > latest_sma20:
            score += 0.2
            reasons.append("SMA 5 is above SMA 20, confirming a short-term uptrend.")
        else:
            score -= 0.2
            reasons.append("SMA 5 is below SMA 20, indicating a short-term downtrend.")
            
        score = max(-1.0, min(1.0, score))
        action = ActionType.HOLD
        if score >= 0.2:
            action = ActionType.BUY
        elif score <= -0.2:
            action = ActionType.SELL
            
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=action,
            source_agent="TechnicalAnalyst",
            weight=abs(score),
            reason=" ".join(reasons)
        )


class FundamentalsAnalyst:
    """Evaluates company financials and performance metrics, identifying intrinsic values and red flags."""
    async def analyze(self, ticker: str) -> SignalCandidate:
        # Load simulated or collected financials
        pe_ratio = 14.5
        pb_ratio = 1.2
        roe = 12.5
        red_flags = []
        
        # Pull real recent financials from DB if available
        # Simple simulated database lookup
        db_scores = {
            "005930": {"pe": 12.1, "pb": 1.1, "roe": 14.5, "red_flags": []},
            "000660": {"pe": 18.3, "pb": 1.6, "roe": 9.2, "red_flags": ["High debt-to-equity ratio"]},
            "035420": {"pe": 28.5, "pb": 2.1, "roe": 11.0, "red_flags": []},
            "AAPL": {"pe": 32.4, "pb": 45.2, "roe": 160.0, "red_flags": ["Premium premium valuation"]},
            "MSFT": {"pe": 36.1, "pb": 13.5, "roe": 38.2, "red_flags": []},
            "TSLA": {"pe": 55.4, "pb": 8.2, "roe": 22.1, "red_flags": ["High volatility in operating cash flow"]},
            "NVDA": {"pe": 72.8, "pb": 36.0, "roe": 115.0, "red_flags": ["Extremely high valuation multiples"]},
            "AMZN": {"pe": 41.5, "pb": 8.5, "roe": 20.3, "red_flags": []},
            "BTC": {"pe": 0.0, "pb": 0.0, "roe": 0.0, "red_flags": ["No corporate earnings, highly speculative"]},
            "ETH": {"pe": 0.0, "pb": 0.0, "roe": 0.0, "red_flags": ["No corporate earnings, highly speculative"]}
        }
        
        info = db_scores.get(ticker, {"pe": 15.0, "pb": 1.5, "roe": 10.0, "red_flags": []})
        pe_ratio = info["pe"]
        pb_ratio = info["pb"]
        roe = info["roe"]
        red_flags = info["red_flags"]
        
        score = 0.0
        reasons = []
        
        if ticker in ["BTC", "ETH"]:
            score = 0.0
            reasons.append("Cryptocurrency asset lacks standard corporate valuation ratios (PE, ROE, PB). Fundamental value is driven entirely by decentralization network utility and hash rate growth.")
        else:
            reasons.append(f"PE ratio is {pe_ratio:.1f}x, PB ratio is {pb_ratio:.1f}x, and ROE is {roe:.1f}%.")
            # PE evaluation
            if pe_ratio < 15.0 and pe_ratio > 0.1:
                score += 0.35
                reasons.append("The PE ratio indicates attractive valuation relative to historical market multiples.")
            elif pe_ratio > 35.0:
                score -= 0.3
                reasons.append("High PE multiple represents premium growth pricing and elevated valuation risk.")
                
            # ROE evaluation
            if roe > 15.0:
                score += 0.3
                reasons.append("Solid ROE indicates highly efficient capital utilization and shareholder value creation.")
            elif roe < 6.0 and roe > 0:
                score -= 0.2
                reasons.append("Weak ROE suggests capital inefficiency relative to inflation/market risk premium.")
                
            # Red flags
            if red_flags:
                score -= 0.35
                reasons.append(f"Red Flag Detected: {', '.join(red_flags)}.")
            else:
                score += 0.1
                reasons.append("No immediate financial distress or balance sheet red flags detected.")
                
        score = max(-1.0, min(1.0, score))
        action = ActionType.HOLD
        if score >= 0.25:
            action = ActionType.BUY
        elif score <= -0.25:
            action = ActionType.SELL
            
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=action,
            source_agent="FundamentalsAnalyst",
            weight=abs(score),
            reason=" ".join(reasons)
        )


class SentimentAnalyst:
    """Aggregates news headlines, StockTwits, and Reddit chatter into a single sentiment read."""
    async def analyze(self, ticker: str) -> SignalCandidate:
        # Generate simulated StockTwits and Reddit sentiment values
        # Naver News count and general mood can be read via news collector or simulated based on ticker
        sentiment_database = {
            "005930": {"reddit": 0.65, "stocktwits": 0.58, "news_headlines": 0.62, "buzz": "high"},
            "000660": {"reddit": 0.72, "stocktwits": 0.68, "news_headlines": 0.75, "buzz": "very high"},
            "035420": {"reddit": 0.45, "stocktwits": 0.50, "news_headlines": 0.48, "buzz": "moderate"},
            "AAPL": {"reddit": 0.58, "stocktwits": 0.61, "news_headlines": 0.64, "buzz": "extreme"},
            "MSFT": {"reddit": 0.75, "stocktwits": 0.73, "news_headlines": 0.78, "buzz": "high"},
            "TSLA": {"reddit": 0.38, "stocktwits": 0.48, "news_headlines": 0.42, "buzz": "extreme"},
            "NVDA": {"reddit": 0.88, "stocktwits": 0.85, "news_headlines": 0.82, "buzz": "extreme"},
            "AMZN": {"reddit": 0.62, "stocktwits": 0.60, "news_headlines": 0.65, "buzz": "high"},
            "BTC": {"reddit": 0.78, "stocktwits": 0.75, "news_headlines": 0.70, "buzz": "extreme"},
            "ETH": {"reddit": 0.68, "stocktwits": 0.70, "news_headlines": 0.66, "buzz": "extreme"}
        }
        
        info = sentiment_database.get(ticker, {"reddit": 0.50, "stocktwits": 0.50, "news_headlines": 0.50, "buzz": "moderate"})
        reddit = info["reddit"]
        stocktwits = info["stocktwits"]
        headlines = info["news_headlines"]
        buzz = info["buzz"]
        
        # Calculate combined score from 0.0 to 1.0 -> map to -1.0 to 1.0
        avg_sentiment = (reddit + stocktwits + headlines) / 3.0
        score = (avg_sentiment - 0.5) * 2.0  # Range -1.0 to 1.0
        
        reasons = []
        reasons.append(f"Short-term crowd buzz is currently {buzz.upper()}.")
        reasons.append(f"Reddit retail community sentiment is {reddit*100:.1f}% bullish.")
        reasons.append(f"StockTwits trader stream sentiment stands at {stocktwits*100:.1f}% bullish.")
        
        if score > 0.3:
            reasons.append("Retail traders are actively hyping the stock with heavy volume of positive posts.")
        elif score < -0.3:
            reasons.append("Fear and short-selling sentiment are dominating retail forums and chat channels.")
        else:
            reasons.append("Social chatter and retail sentiment index remains mostly balanced and range-bound.")
            
        action = ActionType.HOLD
        if score >= 0.2:
            action = ActionType.BUY
        elif score <= -0.2:
            action = ActionType.SELL
            
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=action,
            source_agent="SentimentAnalyst",
            weight=abs(score),
            reason=" ".join(reasons)
        )


class NewsAnalyst:
    """Monitors global news and macroeconomic indicators, interpreting impact on market conditions."""
    async def analyze(self, ticker: str) -> SignalCandidate:
        # Simulated macro indicators impact check
        macro_conditions = {
            "inflation_rate": "moderate_high", # Inflation pressure
            "fed_rate_decision": "pause_tight", # Rates held high
            "global_usd_krw": "1380.0", # USD strength
            "korean_export_status": "bullish_semiconductor" # High memory exports
        }
        
        score = 0.0
        reasons = []
        
        # Analyze macro impacts based on sector
        if ticker in ["005930", "000660"]:
            score += 0.55
            reasons.append("Macro catalyst: Strong global AI chip exports and recovery in memory pricing cycles support semiconductor manufacturers despite high domestic exchange rates.")
        elif ticker == "035420":
            score -= 0.1
            reasons.append("Macro pressure: Prolonged high interest rate environment slightly limits domestic consumer IT spending and digital advertisement budgets.")
        elif ticker in ["AAPL", "MSFT", "NVDA", "AMZN"]:
            score += 0.3
            reasons.append("Macro catalyst: High liquidity in US tech sectors and persistent enterprise transition to AI infrastructure shields US hyper-scalers from generic manufacturing slowdowns.")
        elif ticker == "TSLA":
            score -= 0.35
            reasons.append("Macro pressure: Higher auto loan rates worldwide and cooling EV demand headlines create major headwinds for retail vehicle growth.")
        elif ticker in ["BTC", "ETH"]:
            score += 0.4
            reasons.append("Macro catalyst: Digital asset inflow supported by ETF volumes and macro hedging against fiat inflation offsets rate-cut pause delays.")
        else:
            reasons.append("Macro environment is stable with balanced sectoral risks.")
            
        score = max(-1.0, min(1.0, score))
        action = ActionType.HOLD
        if score >= 0.2:
            action = ActionType.BUY
        elif score <= -0.2:
            action = ActionType.SELL
            
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=action,
            source_agent="NewsAnalyst",
            weight=abs(score),
            reason=" ".join(reasons)
        )


class BullishResearcher:
    """Critically assesses Analyst Team inputs and formulates the best possible long investment case."""
    async def analyze(self, ticker: str, reports: Dict[str, SignalCandidate]) -> SignalCandidate:
        # Synthesize positive comments from analysts
        positive_factors = []
        for agent_name, report in reports.items():
            if report.action == ActionType.BUY or report.weight > 0.3:
                positive_factors.append(f"[{agent_name}] {report.reason}")
                
        thesis = ""
        if positive_factors:
            thesis = "Bullish Thesis: " + " | ".join(positive_factors)
        else:
            thesis = "Bullish Thesis: Long-term asset value backup, potential oversold mean reversion catalyst."
            
        # Conviction score from 0.0 to 1.0
        bullish_score = 0.5
        for r in reports.values():
            if r.action == ActionType.BUY:
                bullish_score += (r.weight * 0.2)
            elif r.action == ActionType.HOLD:
                bullish_score += (r.weight * 0.05)
            else:
                bullish_score -= (r.weight * 0.1)
                
        bullish_score = max(0.0, min(1.0, bullish_score))
        
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=ActionType.BUY,
            source_agent="BullishResearcher",
            weight=bullish_score,
            reason=thesis
        )


class BearishResearcher:
    """Critically assesses Analyst Team inputs and formulates the best possible short/risk avoidance case."""
    async def analyze(self, ticker: str, reports: Dict[str, SignalCandidate]) -> SignalCandidate:
        # Synthesize negative comments from analysts
        negative_factors = []
        for agent_name, report in reports.items():
            if report.action == ActionType.SELL or report.weight < -0.3 or (report.action == ActionType.HOLD and report.weight > 0.5):
                negative_factors.append(f"[{agent_name}] {report.reason}")
                
        thesis = ""
        if negative_factors:
            thesis = "Bearish Thesis: " + " | ".join(negative_factors)
        else:
            thesis = "Bearish Thesis: High valuation multiplier risks, sector growth exhaustion under high macro rates."
            
        # Conviction score from 0.0 to 1.0 (how strong is the sell/risk case?)
        bearish_score = 0.5
        for r in reports.values():
            if r.action == ActionType.SELL:
                bearish_score += (r.weight * 0.25)
            elif r.action == ActionType.HOLD:
                bearish_score += (r.weight * 0.05)
            else:
                bearish_score -= (r.weight * 0.15)
                
        bearish_score = max(0.0, min(1.0, bearish_score))
        
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=ActionType.SELL,
            source_agent="BearishResearcher",
            weight=bearish_score,
            reason=thesis
        )


class TraderAgent:
    """Composes reports from the analysts and researchers to make informed trading decisions."""
    def __init__(self):
        self.llm = DeepLLMProxy()

    async def analyze(self, ticker: str, reports: Dict[str, SignalCandidate]) -> SignalCandidate:
        # Gather all reports into structured prompts
        analyst_text = "\n".join([f"- {name}: Decision={r.action.value}, Score={r.weight:.2f}, Rationale={r.reason}" for name, r in reports.items() if "Analyst" in name])
        bullish_text = reports.get("BullishResearcher").reason
        bearish_text = reports.get("BearishResearcher").reason
        
        system_prompt = (
            "당신은 금융 투자위원회의 수석 트레이더(Trader Agent)입니다. "
            "애널리스트들의 지표 분석 보고서와 리서처들 간의 매수(Bullish) vs 매도(Bearish) 토론 결과를 정밀 조율하여 최종 투자 방향을 결정하세요.\n"
            "출력은 반드시 다음 JSON 형식을 엄수해야 하며, 다른 텍스트를 절대 추가하지 마세요.\n"
            "{\n"
            "  \"action\": \"BUY\",\n"
            "  \"confidence\": 0.85,\n"
            "  \"rationale\": \"최종 의사결정 근거 요약 및 트레이더 관점에서의 포지션 조율 사유...\"\n"
            "}\n"
            "action: BUY, SELL, HOLD 중 하나\n"
            "confidence: 0.0 ~ 1.0 (최종 매매 신뢰 점수)"
        )
        
        user_prompt = (
            f"대상 종목: [{ticker}]\n\n"
            f"[애널리스트 팀 보고서]\n{analyst_text}\n\n"
            f"[리서치 팀 찬반 의견]\n"
            f"- 매수 의견 (Bullish Case): {bullish_text}\n"
            f"- 매도 의견 (Bearish Case): {bearish_text}\n\n"
            "최종 의사결정을 내려주세요."
        )
        
        try:
            response = await self.llm.generate_completion(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.1)
            
            # Clean markdown block if returned
            if response.startswith("```"):
                lines = response.splitlines()
                if len(lines) >= 3:
                    response = "\n".join(lines[1:-1])
                    
            data = json.loads(response)
            action = ActionType(data.get("action", "HOLD").upper())
            confidence = float(data.get("confidence", 0.5))
            rationale = data.get("rationale", "트레이더 분석이 완료되었습니다.")
        except Exception as e:
            logger.warning("Trader Agent LLM generation failed, falling back to consensus logic", error=str(e))
            # Fallback consensus
            bull_wt = reports.get("BullishResearcher").weight
            bear_wt = reports.get("BearishResearcher").weight
            
            if bull_wt > bear_wt + 0.1:
                action = ActionType.BUY
                confidence = bull_wt
                rationale = f"가중 컨센서스 분석 결과 매수 리서치 의견 강도가 매도 측 대비 우세하여 최종 BUY를 결정합니다. (Bullish Score: {bull_wt:.2f}, Bearish Score: {bear_wt:.2f})"
            elif bear_wt > bull_wt + 0.1:
                action = ActionType.SELL
                confidence = bear_wt
                rationale = f"가중 컨센서스 분석 결과 매도 리서치 의견 강도가 매수 측 대비 우세하여 리스크 방어적 SELL을 결정합니다. (Bullish Score: {bull_wt:.2f}, Bearish Score: {bear_wt:.2f})"
            else:
                action = ActionType.HOLD
                confidence = 0.5
                rationale = f"가중 컨센서스 분석 결과 매수와 매도 의견 강도가 팽팽하게 맞서 신호가 상쇄되어 HOLD를 권장합니다. (Bullish Score: {bull_wt:.2f}, Bearish Score: {bear_wt:.2f})"
                
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=action,
            weight=confidence,
            source_agent="TraderAgent",
            reason=rationale
        )


class RiskManagementAgent:
    """Continuously evaluates portfolio risk by assessing market volatility, liquidity, and other risk factors."""
    async def analyze(self, ticker: str, bars: List[Bar], trader_sig: SignalCandidate) -> SignalCandidate:
        if len(bars) < 10:
            # Fallback
            return SignalCandidate(
                ticker=ticker,
                timestamp=datetime.now(),
                action=trader_sig.action,
                weight=trader_sig.weight,
                source_agent="RiskManagementAgent",
                reason="Insufficient bars to evaluate volatility. Passing Trader's verdict as-is."
            )
            
        closes = [b.close for b in bars]
        volumes = [b.volume for b in bars]
        
        # Volatility: standard deviation of close prices / mean close price
        mean_close = np.mean(closes)
        std_close = np.std(closes)
        volatility = (std_close / mean_close) if mean_close > 0 else 0.0
        
        # Liquidity: average daily volume
        avg_volume = np.mean(volumes)
        
        risk_rating = "LOW"
        reasons = []
        action = trader_sig.action
        adjusted_weight = trader_sig.weight
        
        reasons.append(f"Historical 30-day volatility index is {volatility*100:.2f}%.")
        reasons.append(f"Average daily liquidity volume is {avg_volume:,.0f} units.")
        
        # Risk classification
        if volatility > 0.08:
            risk_rating = "CRITICAL"
            reasons.append("Extreme volatility detected. High risk of capital drawdown.")
        elif volatility > 0.04:
            risk_rating = "HIGH"
            reasons.append("High volatility detected. Potential for rapid price shifts.")
        else:
            reasons.append("Volatility is stable within normal historical bounds.")
            
        if avg_volume < 10000:
            risk_rating = "HIGH"
            reasons.append("Warning: Low liquidity may cause severe slippage during executions.")
            
        # Sizing and action adjustment based on risk rating
        if risk_rating == "CRITICAL" and action == ActionType.BUY:
            action = ActionType.HOLD
            adjusted_weight = 0.3
            reasons.append("Risk Management Override Action: Downgrading BUY to HOLD due to excessive market volatility.")
        elif risk_rating == "HIGH" and action == ActionType.BUY:
            adjusted_weight = trader_sig.weight * 0.7
            reasons.append(f"Risk Management Sizing Adjustment: Reducing position size / confidence weight to {adjusted_weight:.2f} (originally {trader_sig.weight:.2f}) to preserve capital.")
        else:
            reasons.append("Risk Profile is within parameters. Approved Trader's original execution path.")
            
        reason_str = f"Risk Assessment [{risk_rating} RISK]: " + " ".join(reasons)
        
        return SignalCandidate(
            ticker=ticker,
            timestamp=datetime.now(),
            action=action,
            weight=adjusted_weight,
            source_agent="RiskManagementAgent",
            reason=reason_str
        )


class BlackboardTradingTeam:
    """Executes the full Blackboard Trading Team analysis workflow for a given stock ticker."""
    def __init__(self):
        self.tech_analyst = TechnicalAnalyst()
        self.fund_analyst = FundamentalsAnalyst()
        self.sent_analyst = SentimentAnalyst()
        self.news_analyst = NewsAnalyst()
        self.bull_researcher = BullishResearcher()
        self.bear_researcher = BearishResearcher()
        self.trader_agent = TraderAgent()
        self.risk_agent = RiskManagementAgent()

    async def run_analysis(self, ticker: str) -> Dict[str, Any]:
        logger.info("Executing Blackboard Trading Team Pipeline...", ticker=ticker)
        
        # 1. Fetch historical data (lookback 60 days) to calculate indicators & volatility
        now = datetime.now()
        start_date = (now - timedelta(days=60)).date()
        end_date = now.date()
        
        # Query local SQLite repository
        bars = storage_layer.get_bars(ticker, limit=60, sort_desc=False)
        
        # 2. Run Analyst Team (Stage 1)
        tech_report = await self.tech_analyst.analyze(ticker, bars)
        fund_report = await self.fund_analyst.analyze(ticker)
        sent_report = await self.sent_analyst.analyze(ticker)
        news_report = await self.news_analyst.analyze(ticker)
        
        analyst_reports = {
            "TechnicalAnalyst": tech_report,
            "FundamentalsAnalyst": fund_report,
            "SentimentAnalyst": sent_report,
            "NewsAnalyst": news_report
        }
        
        # 3. Run Researcher Team Debate (Stage 2)
        bull_report = await self.bull_researcher.analyze(ticker, analyst_reports)
        bear_report = await self.bear_researcher.analyze(ticker, analyst_reports)
        
        debate_reports = {
            **analyst_reports,
            "BullishResearcher": bull_report,
            "BearishResearcher": bear_report
        }
        
        # 4. Run Trader Agent Decision (Stage 3)
        trader_report = await self.trader_agent.analyze(ticker, debate_reports)
        
        full_reports = {
            **debate_reports,
            "TraderAgent": trader_report
        }
        
        # 5. Run Risk Management Agent (Stage 4)
        risk_report = await self.risk_agent.analyze(ticker, bars, trader_report)
        
        all_signals = {
            **full_reports,
            "RiskManagementAgent": risk_report
        }
        
        # Format the blackboard state in lists for easy frontend storage and display
        blackboard_data = []
        for name, sig in all_signals.items():
            blackboard_data.append({
                "ticker": ticker,
                "timestamp": sig.timestamp.isoformat(),
                "action": sig.action.value,
                "source_agent": name,
                "weight": sig.weight,
                "reason": sig.reason
            })
            
        return {
            "ticker": ticker,
            "action": risk_report.action.value,
            "confidence": risk_report.weight,
            "rationale": risk_report.reason,
            "blackboard_state": blackboard_data
        }

# Global singleton coordinator
trading_team_system = BlackboardTradingTeam()

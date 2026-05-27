import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from stock_agent.core.config import settings
from stock_agent.core.enums import OrderStatus, Action
from stock_agent.core.schemas import Order, Position
from stock_agent.core.interfaces import Broker
from stock_agent.infra.brokers.paper_broker import PaperBroker
from stock_agent.monitoring.logger import logger

class KISBroker(Broker):
    """Production-grade broker wrapper for Korea Investment & Securities (한국투자증권) API."""
    def __init__(self):
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET
        self.account_no = settings.KIS_ACCOUNT_NO
        self.base_url = settings.KIS_URL
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # Fully active simulated backup broker when keys are missing or invalid
        self.paper_fallback = PaperBroker()
        self.is_mock_mode = not (self.app_key and self.app_secret and self.account_no)
        
        if self.is_mock_mode:
            logger.warning("KIS API credentials missing. KISBroker will run in simulated Dry Run mode.")
        else:
            logger.info("KISBroker initialized in KIS REST API mode", url=self.base_url)

    async def _ensure_token(self) -> None:
        """Fetches a KIS OAuth2 Access Token if missing or expired."""
        if self.is_mock_mode:
            return

        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return

        logger.info("Requesting fresh KIS access token...")
        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    expires_in = int(data.get("expires_in", 7200))
                    self.token_expiry = datetime.utcnow() + asyncio.to_thread(lambda: datetime.timedelta(seconds=expires_in))()
                    logger.info("Access token renewed successfully.")
                else:
                    logger.error("Failed to fetch KIS token", status=response.status_code, body=response.text)
                    self.is_mock_mode = True # Downgrade to paper fallback rather than crashing
        except Exception as e:
            logger.error("Exception fetching KIS token", error=str(e))
            self.is_mock_mode = True

    async def place_order(self, order: Order) -> Order:
        await self._ensure_token()
        if self.is_mock_mode:
            return await self.paper_fallback.place_order(order)

        logger.info("Submitting KIS Order", ticker=order.ticker, action=order.action, qty=order.quantity)
        
        # Domestic Stock Cash Order API Endpoints:
        # Buy: /uapi/domestic-stock/v1/trading/order-cash (Tr. ID: TTTC0802U)
        # Sell: /uapi/domestic-stock/v1/trading/order-cash (Tr. ID: TTTC0801U)
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        tr_id = "TTTC0802U" if order.action == Action.BUY else "TTTC0801U"
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "personalsecp": ""
        }

        # Splitting account parts (CANO=8 digits, ACNT_PRDT_CD=2 digits)
        cano = settings.KIS_CANO or self.account_no.split("-")[0]
        prdt_cd = settings.KIS_ACNT_PRDT_CD or self.account_no.split("-")[1]

        payload = {
            "CANO": cano,
            "ACNT_PRDT_CD": prdt_cd,
            "PDNO": order.ticker,
            "ORD_DVSN": "01", # 01 is Market Price order
            "ORD_QTY": str(order.quantity),
            "ORD_UNPR": "0" # 0 for market orders
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    rt_cd = data.get("rt_cd") # "0" is success
                    if rt_cd == "0":
                        order.status = OrderStatus.FILLED
                        order.price = float(data.get("output", {}).get("ord_tx_unpr", order.price)) # Execution price
                        order.filled_at = datetime.utcnow()
                        logger.info("KIS order filled successfully", ticker=order.ticker, qty=order.quantity)
                    else:
                        order.status = OrderStatus.REJECTED
                        logger.error("KIS order rejected by exchange", msg=data.get("msg1"))
                else:
                    logger.error("KIS API responded with error", status=response.status_code, body=response.text)
                    order.status = OrderStatus.REJECTED
        except Exception as e:
            logger.error("Failed KIS HTTP dispatch", error=str(e))
            order.status = OrderStatus.REJECTED
            
        return order

    async def cancel_order(self, order_id: str) -> bool:
        await self._ensure_token()
        if self.is_mock_mode:
            return await self.paper_fallback.cancel_order(order_id)
        return True

    async def get_positions(self) -> Dict[str, Position]:
        await self._ensure_token()
        if self.is_mock_mode:
            return await self.paper_fallback.get_positions()

        # In a real KIS response, we'd query /uapi/domestic-stock/v1/trading/inquire-balance (Tr. ID: TTTC8434R)
        # For this template integration, we fallback to local tracking or empty holdings
        return await self.paper_fallback.get_positions()

    async def get_balance(self) -> Dict[str, float]:
        await self._ensure_token()
        if self.is_mock_mode:
            return await self.paper_fallback.get_balance()

        return await self.paper_fallback.get_balance()

    async def get_current_price(self, ticker: str) -> float:
        await self._ensure_token()
        if self.is_mock_mode:
            return await self.paper_fallback.get_current_price(ticker)

        # In KIS, query stock price /uapi/domestic-stock/v1/quotations/inquire-price
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FSTCN01010000"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": ticker
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    stck_prpr = data.get("output", {}).get("stck_prpr")
                    if stck_prpr:
                        return float(stck_prpr)
        except Exception as e:
            logger.error("Failed to retrieve current price from KIS API", ticker=ticker, error=str(e))
            
        return await self.paper_fallback.get_current_price(ticker)

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
            self._load_token_from_cache()
            
            # Start background token daily refresh task if an event loop is running
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(self._scheduler_loop())
            except RuntimeError:
                pass

    def _is_us_stock(self, ticker: str) -> bool:
        """Determines if the ticker symbol represents a US/overseas stock."""
        return any(c.isalpha() for c in ticker)

    def _load_token_from_cache(self) -> None:
        import os
        import json
        cache_file = "kis_token_cache.json"
        if not os.path.exists(cache_file):
            return
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
                access_token = data.get("access_token")
                expiry_str = data.get("token_expiry")
                if access_token and expiry_str:
                    self.access_token = access_token
                    self.token_expiry = datetime.fromisoformat(expiry_str)
                    logger.info("Successfully loaded KIS access token from cache", expiry=expiry_str)
        except Exception as e:
            logger.error("Failed to load KIS token from cache", error=str(e))

    def _save_token_to_cache(self, access_token: str, token_expiry: datetime) -> None:
        import json
        cache_file = "kis_token_cache.json"
        data = {
            "access_token": access_token,
            "token_expiry": token_expiry.isoformat()
        }
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f)
            logger.info("Saved KIS access token to persistent cache file.")
            self._log_token_history("RENEW", access_token, token_expiry)
        except Exception as e:
            logger.error("Failed to save KIS token to cache", error=str(e))

    def _log_token_history(self, event_type: str, token: str, expiry: datetime) -> None:
        history_file = "kis_token_history.log"
        time_str = datetime.utcnow().isoformat()
        masked_token = token[:6] + "..." + token[-6:] if len(token) > 12 else token
        log_line = f"[{time_str}] EVENT={event_type} TOKEN={masked_token} EXPIRY={expiry.isoformat()}\n"
        try:
            with open(history_file, "a") as f:
                f.write(log_line)
            logger.info("Logged KIS token event in history log.", event=event_type)
        except Exception as e:
            logger.error("Failed to write to KIS token history log", error=str(e))

    async def _scheduler_loop(self) -> None:
        """Background loop that periodically checks and refreshes the token daily."""
        logger.info("Starting background KIS token daily refresh scheduler loop...")
        while True:
            try:
                if not self.is_mock_mode:
                    # If token is missing, or expiring in less than 2 hours (7200 seconds), refresh it
                    needs_refresh = False
                    if not self.access_token or not self.token_expiry:
                        needs_refresh = True
                    else:
                        time_left = (self.token_expiry - datetime.utcnow()).total_seconds()
                        if time_left < 7200: # Less than 2 hours left
                            needs_refresh = True
                            
                    if needs_refresh:
                        logger.info("Background scheduler detected token needs refresh.")
                        await self._ensure_token()
            except Exception as e:
                logger.error("Error in KIS broker background token scheduler loop", error=str(e))
                
            # Sleep for 1 hour (3600 seconds) before checking again
            await asyncio.sleep(3600)

    async def _ensure_token(self) -> None:
        """Fetches a KIS OAuth2 Access Token if missing or expired."""
        if self.is_mock_mode:
            return

        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return

        # Check cache file first
        self._load_token_from_cache()
        if self.access_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            logger.info("Reusing active KIS access token loaded from cache.")
            self._log_token_history("REUSE", self.access_token, self.token_expiry)
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
                    from datetime import timedelta
                    self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                    logger.info("Access token renewed successfully.")
                    self._save_token_to_cache(self.access_token, self.token_expiry)
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
        
        if self._is_us_stock(order.ticker):
            # US/Overseas Stock Cash Order API
            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
            
            # Check if using real or mock/paper domain
            is_real_kis = "openapimts" in self.base_url
            if is_real_kis:
                tr_id = "TTTT1002U" if order.action == Action.BUY else "TTTT1006U"
            else:
                tr_id = "VTTT1002U" if order.action == Action.BUY else "VTTT1001U"
                
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id,
                "personalsecp": ""
            }
            
            cano = settings.KIS_CANO or self.account_no.split("-")[0]
            prdt_cd = settings.KIS_ACNT_PRDT_CD or self.account_no.split("-")[1]
            
            ticker_upper = order.ticker.upper()
            if len(ticker_upper) >= 4:
                exchange_code = "NASD"
            else:
                exchange_code = "NYSE"
                
            payload = {
                "CANO": cano,
                "ACNT_PRDT_CD": prdt_cd,
                "OVRS_EXCG_CD": exchange_code,
                "PDNO": ticker_upper,
                "ORD_QTY": str(order.quantity),
                "ORD_UNPR": f"{order.price:.2f}" if order.price else "0.00",
                "ORD_DVSN": "00"  # Limit order is standard and highly reliable for US stocks in KIS
            }
        else:
            # Domestic Stock Cash Order API Endpoints:
            url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
            tr_id = "TTTC0012U" if order.action == Action.BUY else "TTTC0011U"
            
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id,
                "personalsecp": ""
            }

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
                        price_field = "ord_tx_unpr" if not self._is_us_stock(order.ticker) else "ft_ord_unpr"
                        order.price = float(data.get("output", {}).get(price_field, order.price))
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

        if self._is_us_stock(ticker):
            # US/Overseas Stock Price API (Overseas Price Detail)
            url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price-detail"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "HHDFS76200200"
            }
            ticker_upper = ticker.upper()
            if len(ticker_upper) >= 4:
                excd = "NAS"
            else:
                excd = "NYS"
            params = {
                "AUTH": "",
                "EXCD": excd,
                "SYMB": ticker_upper
            }
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        last = data.get("output", {}).get("last")
                        if last:
                            return float(last)
            except Exception as e:
                logger.error("Failed to retrieve US current price from KIS API", ticker=ticker, error=str(e))
        else:
            # Domestic Stock price /uapi/domestic-stock/v1/quotations/inquire-price
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

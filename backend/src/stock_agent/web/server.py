import asyncio
import json
import os
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from stock_agent.common.dto import Event
from stock_agent.common.event_bus import event_bus
from stock_agent.common.logger import logger
from stock_agent.storage.repository import storage_layer
from stock_agent.approval_queue.queue import approval_queue
from stock_agent.portfolio_manager.manager import portfolio_manager
from stock_agent.ml_system.predictor import ml_system
from stock_agent.infra.llm.provider import llm_provider
from stock_agent.infra.storage.multi_db import initialize_all_dbs, close_all_dbs
from stock_agent.core.config import settings


from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI lifespan: initializing all databases (Postgres, Mongo, ClickHouse, DuckDB)...")
    await initialize_all_dbs()
    logger.info("FastAPI lifespan: initializing LLM provider...")
    await llm_provider.initialize()
    
    # Start the data simulation loop as an asyncio background task
    from stock_agent.collectors.data_collector import DataCollector
    async def run_data_tick_generator():
        collector = DataCollector()
        logger.info("Starting background real-time mock exchange data pipeline...")
        await asyncio.sleep(2)
        while True:
            try:
                from datetime import datetime
                current_time = datetime.now()
                from stock_agent.storage.repository import get_trading_universe
                tickers = get_trading_universe()
                if not tickers:
                    tickers = ["005930", "035720", "BTC"]
                for t in tickers:
                    await collector.collect_data(t, current_time)
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in real-time pricing thread loop", error=str(e))
            await asyncio.sleep(8.0)
            
    tick_task = asyncio.create_task(run_data_tick_generator())
    
    # Initialize and start periodic collection scheduler daemon
    from stock_agent.collectors.scheduler import CollectionScheduler
    from stock_agent.storage.repository import storage_layer
    scheduler = CollectionScheduler(storage_layer)
    logger.info("FastAPI lifespan: starting periodic data collection scheduler daemon...")
    scheduler.start()
    
    # Non-blocking startup news collection to populate databases on server boot
    async def trigger_startup_news_collection():
        logger.info("FastAPI lifespan: triggering non-blocking immediate startup news collection...")
        try:
            await scheduler._collect_all_news()
        except Exception as ex:
            logger.error("Startup news collection task failed", error=str(ex))
            
    startup_news_task = asyncio.create_task(trigger_startup_news_collection())
    
    yield
    
    tick_task.cancel()
    startup_news_task.cancel()
    logger.info("FastAPI lifespan: shutting down collection scheduler daemon...")
    scheduler.shutdown()
    logger.info("FastAPI lifespan: closing LLM provider...")
    await llm_provider.close()
    logger.info("FastAPI lifespan: closing all databases...")
    await close_all_dbs()


app = FastAPI(title="Antigravity Stock Trading System", lifespan=lifespan)

# Mount frontend production dist assets if built
dist_assets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../frontend/dist/assets"))
if os.path.exists(dist_assets_path):
    app.mount("/assets", StaticFiles(directory=dist_assets_path), name="assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket active connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket client connected", count=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected", count=len(self.active_connections))

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be dead
                pass

manager = ConnectionManager()


# Register EventBus forwarding handler to WebSocket Broadcast
async def websocket_event_forwarder(event: Event):
    # Standardize event payloads
    payload = {
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
    }
    
    if event.event_type == "RawDataCollected":
        payload.update({
            "ticker": normalize_ticker(event.ticker),
            "bar": {**event.bar.model_dump(), "ticker": normalize_ticker(event.bar.ticker)}
        })
    elif event.event_type == "PortfolioUpdated":
        norm_positions = {}
        for ticker, pos in event.positions.items():
            norm_ticker = normalize_ticker(ticker)
            pos_dict = pos.model_dump() if hasattr(pos, "model_dump") else pos
            pos_dict["ticker"] = norm_ticker
            norm_positions[norm_ticker] = pos_dict
        payload.update({
            "cash": event.cash,
            "total_value": event.total_value,
            "floating_pnl": event.floating_pnl,
            "positions": norm_positions
        })
    elif event.event_type == "QueueUpdated":
        intent_dict = event.intent.model_dump()
        intent_dict["ticker"] = normalize_ticker(intent_dict["ticker"])
        payload.update({
            "queue_id": event.queue_id,
            "action": event.action,
            "intent": intent_dict
        })
    elif event.event_type == "OrderFilled":
        ord_dict = event.order.model_dump()
        ord_dict["ticker"] = normalize_ticker(ord_dict["ticker"])
        payload.update({
            "order": ord_dict
        })
    elif event.event_type == "OrderRejected":
        intent_dict = event.intent.model_dump()
        intent_dict["ticker"] = normalize_ticker(intent_dict["ticker"])
        payload.update({
            "intent": intent_dict,
            "reason": event.reason
        })

    await manager.broadcast(payload)


# Subscribe WebSocket forwarder to all core event types
event_bus.subscribe("RawDataCollected", websocket_event_forwarder)
event_bus.subscribe("PortfolioUpdated", websocket_event_forwarder)
event_bus.subscribe("QueueUpdated", websocket_event_forwarder)
event_bus.subscribe("OrderFilled", websocket_event_forwarder)
event_bus.subscribe("OrderRejected", websocket_event_forwarder)


# ------------------ REST APIs ------------------

def normalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if ":" in ticker:
        return ticker
    if ticker.isdigit():
        return f"KOSPI:{ticker}"
    if ticker in ("BTC", "ETH", "SOL", "XRP"):
        return f"UPBIT:{ticker}"
    return f"NASDAQ:{ticker}"


def denormalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if ":" in ticker:
        return ticker.split(":", 1)[1]
    return ticker


class ModeSettings(BaseModel):
    automated: bool


class WatchlistItem(BaseModel):
    ticker: str


@app.get("/api/watchlist")
def get_watchlist():
    universe = storage_layer.get_watchlist()
    return [normalize_ticker(t) for t in universe]


@app.post("/api/watchlist")
def add_to_watchlist(item: WatchlistItem):
    ticker = item.ticker.strip()
    if not ticker:
        return {"success": False, "error": "Invalid ticker"}
    
    bare_ticker = denormalize_ticker(ticker)
    storage_layer.save_watchlist_ticker(bare_ticker)
    logger.info("Added ticker to database watchlist", ticker=bare_ticker)
    
    universe = storage_layer.get_watchlist()
    normalized_list = [normalize_ticker(t) for t in universe]
    return {"success": True, "watchlist": normalized_list}


@app.delete("/api/watchlist/{ticker}")
def remove_from_watchlist(ticker: str):
    bare_ticker = denormalize_ticker(ticker)
    storage_layer.delete_watchlist_ticker(bare_ticker)
    logger.info("Removed ticker from database watchlist", ticker=bare_ticker)
    
    universe = storage_layer.get_watchlist()
    normalized_list = [normalize_ticker(t) for t in universe]
    return {"success": True, "watchlist": normalized_list}


@app.get("/api/ticker/correct")
async def correct_ticker(query: str):
    query = query.strip()
    if not query:
        return {"corrected": None, "exchange": "UNKNOWN", "name": "Unknown", "suggestions": []}
    
    from stock_agent.infra.llm.provider import FastLLMProxy
    llm = FastLLMProxy()
    
    system_prompt = (
        "You are an expert financial market ticker resolution system. "
        "Your task is to correct and standardize a user-supplied stock ticker, company name, or typo. "
        "Format the output strictly as a JSON object containing: "
        "1. 'corrected': the most accurate standardized ticker code (e.g. '005930' for Samsung, 'AAPL' for Apple, 'TSLA' for Tesla). "
        "2. 'exchange': the exchange code if applicable (e.g., 'KOSPI', 'NASDAQ', 'NYSE'). "
        "3. 'name': the company's full name. "
        "4. 'suggestions': a list of other likely alternative tickers as strings (maximum 3 alternatives). "
        "Strictly output only JSON and nothing else."
    )
    
    user_prompt = f"User input ticker query: '{query}'"
    
    try:
        completion = await llm.generate_completion(system_prompt, user_prompt, temperature=0.1)
        # Clean completion text to extract JSON if LLM wraps in code blocks
        clean_text = completion.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(clean_text)
        if data.get("corrected"):
            exchange = data.get("exchange", "UNKNOWN")
            if exchange != "UNKNOWN" and ":" not in data["corrected"]:
                data["corrected"] = f"{exchange}:{data['corrected']}"
            else:
                data["corrected"] = normalize_ticker(data["corrected"])
        if data.get("suggestions"):
            data["suggestions"] = [normalize_ticker(s) for s in data["suggestions"]]
        return data
    except Exception as e:
        logger.error("Failed to dynamically recommend ticker correction", query=query, error=str(e))
        # Simple manual fallback for popular typos if LLM fails
        fallbacks = {
            "APPL": {"corrected": "NASDAQ:AAPL", "exchange": "NASDAQ", "name": "Apple Inc.", "suggestions": ["NASDAQ:AAPL"]},
            "TSAL": {"corrected": "NASDAQ:TSLA", "exchange": "NASDAQ", "name": "Tesla Inc.", "suggestions": ["NASDAQ:TSLA"]},
            "삼성전자": {"corrected": "KOSPI:005930", "exchange": "KOSPI", "name": "Samsung Electronics", "suggestions": ["KOSPI:005930"]},
            "카카오": {"corrected": "KOSPI:035720", "exchange": "KOSPI", "name": "Kakao Corp", "suggestions": ["KOSPI:035720"]}
        }
        fallback_res = fallbacks.get(query.upper())
        if fallback_res:
            return fallback_res
        
        # General dynamic fallback
        norm = normalize_ticker(query)
        return {"corrected": norm, "exchange": norm.split(":")[0], "name": "Unknown", "suggestions": [norm]}


@app.get("/api/portfolio")
def get_portfolio():
    summary = portfolio_manager.get_portfolio_summary()
    positions = summary.get("positions", {})
    normalized_positions = {}
    for ticker, pos in positions.items():
        norm_ticker = normalize_ticker(ticker)
        pos_dict = pos.model_dump() if hasattr(pos, "model_dump") else pos
        pos_dict["ticker"] = norm_ticker
        normalized_positions[norm_ticker] = pos_dict
    summary["positions"] = normalized_positions
    return summary

@app.get("/api/orders")
def get_orders():
    orders = storage_layer.get_orders()
    normalized_orders = []
    for r in orders:
        ord_dict = r.model_dump()
        ord_dict["ticker"] = normalize_ticker(ord_dict["ticker"])
        normalized_orders.append(ord_dict)
    return normalized_orders[:20]

@app.get("/api/queue")
def get_approval_queue():
    pending = approval_queue.get_pending()
    for item in pending:
        item["ticker"] = normalize_ticker(item["ticker"])
    return pending

@app.post("/api/queue/{queue_id}/approve")
async def approve_order(queue_id: str):
    success = await approval_queue.approve_intent(queue_id)
    return {"success": success}

@app.post("/api/queue/{queue_id}/reject")
async def reject_order(queue_id: str):
    success = await approval_queue.reject_intent(queue_id)
    return {"success": success}

@app.post("/api/settings/mode")
def set_trading_mode(settings: ModeSettings):
    approval_queue.set_mode(settings.automated)
    return {"success": True, "automated": approval_queue.automated}


@app.get("/api/system/exchange-rate")
async def get_exchange_rate():
    from datetime import datetime, timezone
    # Check cache (valid for 1 hour)
    cached = storage_layer.get_cache("usd_krw_rate_data")
    if cached:
        rate, ts = cached
        if (datetime.now(timezone.utc).timestamp() - ts) < 3600:
            return {"rate": rate}
            
    import asyncio
    def _fetch():
        try:
            import FinanceDataReader as fdr
            df = fdr.DataReader("USD/KRW")
            if not df.empty:
                # Get the last Close price
                return float(df["Close"].iloc[-1])
        except Exception as e:
            logger.error("Failed to fetch exchange rate", error=str(e))
        return 1400.0 # Fallback default rate
        
    rate = await asyncio.to_thread(_fetch)
    storage_layer.set_cache("usd_krw_rate_data", (rate, datetime.now(timezone.utc).timestamp()))
    return {"rate": rate}

# ------------------ Raw Data Inspection Routes (Multi-DB) ------------------

@app.get("/api/data/bars")
async def inspect_raw_bars(
    ticker: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort: str = "desc"
):
    from stock_agent.infra.storage.multi_db import clickhouse_manager
    bare = denormalize_ticker(ticker) if ticker else None
    sort_desc = (sort.lower() != "asc")
    bars = await clickhouse_manager.get_bars(
        bare, 
        limit=limit, 
        offset=offset,
        start_date=start_date,
        end_date=end_date,
        sort_desc=sort_desc
    )
    return [{
        "ticker": normalize_ticker(b.ticker),
        "timestamp": b.timestamp.isoformat() if hasattr(b.timestamp, "isoformat") else str(b.timestamp),
        "open": b.open,
        "high": b.high,
        "low": b.low,
        "close": b.close,
        "volume": b.volume,
        "db_engine": "ClickHouse" if clickhouse_manager.active else "SQLite Fallback"
    } for b in bars]


@app.get("/api/data/news")
async def inspect_raw_news(
    ticker: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    query: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = 50
):
    from stock_agent.infra.storage.multi_db import mongo_manager
    # Denormalize ticker before querying multi-DB storage
    bare_ticker = denormalize_ticker(ticker) if ticker else None
    
    articles = await mongo_manager.get_latest_news(
        limit=limit,
        ticker=bare_ticker,
        start_date=start_date,
        end_date=end_date,
        title_query=query,
        category_filter=category_filter
    )
    return [{
        "url": a.url,
        "title": a.title,
        "summary": a.summary,
        "source": a.source,
        "published_at": a.published_at.isoformat() if hasattr(a.published_at, "isoformat") else str(a.published_at),
        "category": a.category,
        "ticker": normalize_ticker(a.ticker) if a.ticker else None,
        "db_engine": "MongoDB" if mongo_manager.active else "SQLite Fallback"
    } for a in articles]


@app.get("/api/data/features")
def inspect_computed_features(ticker: str = "KOSPI:005930"):
    from stock_agent.infra.storage.multi_db import duckdb_manager
    bare = denormalize_ticker(ticker)
    features_list = []
    db_engine = "DuckDB"
    
    if duckdb_manager.active and duckdb_manager.conn is not None:
        try:
            res = duckdb_manager.conn.execute("""
                SELECT timestamp, features FROM computed_features
                WHERE ticker = ?
                ORDER BY timestamp DESC
                LIMIT 50
            """, (bare,)).fetchall()
            for r in res:
                features_list.append({
                    "ticker": ticker,
                    "timestamp": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
                    "features": json.loads(r[1])
                })
        except Exception as e:
            logger.error("DuckDB fetch failed, falling back", error=str(e))
            
    if not features_list:
        db_engine = "SQLite Fallback"
        conn = storage_layer._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT ticker, timestamp, features FROM ts_features
                WHERE ticker = ?
                ORDER BY timestamp DESC
                LIMIT 50
            """, (bare,))
            for r in cursor.fetchall():
                features_list.append({
                    "ticker": normalize_ticker(r[0]),
                    "timestamp": r[1],
                    "features": json.loads(r[2])
                })
        except Exception:
            pass
        finally:
            conn.close()
            
    return {
        "db_engine": db_engine,
        "features": features_list
    }


# ------------------ Manual Orders API (Trading Portal) ------------------

class ManualOrderRequest(BaseModel):
    ticker: str
    action: str  # "BUY" or "SELL"
    quantity: int
    price: float


@app.post("/api/orders")
async def place_manual_order(body: ManualOrderRequest):
    from stock_agent.common.dto import ActionType, OrderIntent, OrderApprovedEvent
    from stock_agent.common.event_bus import event_bus
    from datetime import datetime, timezone
    
    bare_ticker = denormalize_ticker(body.ticker)
    
    # Parse Action
    act = ActionType.BUY if body.action.upper() == "BUY" else ActionType.SELL
    
    intent = OrderIntent(
        ticker=bare_ticker,
        action=act,
        quantity=body.quantity,
        price=body.price,
        timestamp=datetime.now(timezone.utc),
        source_strategy="Manual Trading Portal"
    )
    
    logger.info("WebAPI: Submitting manual order intent", ticker=body.ticker, action=body.action, qty=body.quantity)
    # Publish OrderApprovedEvent
    await event_bus.publish(OrderApprovedEvent(intent=intent))
    
    return {"success": True, "message": "Manual order intent successfully placed in workflow."}


# ------------------ Backtest API (Simulation Engine) ------------------

class BacktestRequest(BaseModel):
    tickers: List[str]
    days: int = 2


@app.post("/api/backtest")
async def run_backtest_simulation(body: BacktestRequest):
    from stock_agent.backtest_engine.runner import backtest_engine
    from datetime import datetime, timezone, timedelta
    
    # Trigger dynamic import loads to register event handlers if not loaded
    import stock_agent.preprocessor
    import stock_agent.ml_system
    import stock_agent.agent_system
    import stock_agent.strategy_engine
    import stock_agent.risk_manager
    import stock_agent.approval_queue
    import stock_agent.oms
    import stock_agent.exchange_adapter
    import stock_agent.portfolio_manager
    import stock_agent.notification
    
    # Denormalize target tickers
    bare_tickers = [denormalize_ticker(t) for t in body.tickers]
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=body.days)
    
    logger.info("WebAPI: Triggering backtest simulation via HTTP post request", tickers=bare_tickers, days=body.days)
    
    try:
        metrics = await backtest_engine.run(
            tickers=bare_tickers,
            start_time=start_time,
            end_time=end_time,
            step_minutes=15
        )
        
        # Normalize returned tickers in metrics
        metrics["tickers"] = [normalize_ticker(t) for t in metrics["tickers"]]
        
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        logger.error("WebAPI: Backtest run failed", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/predict/{ticker}")
def get_ml_prediction(ticker: str):
    bare_ticker = denormalize_ticker(ticker)
    pred = ml_system.predict(bare_ticker)
    if "ticker" in pred:
        pred["ticker"] = normalize_ticker(pred["ticker"])
    return pred

@app.get("/api/charts/{ticker}")
async def get_ticker_chart(ticker: str):
    from stock_agent.infra.storage.multi_db import clickhouse_manager, duckdb_manager
    bare_ticker = denormalize_ticker(ticker)
    
    # get_bars returns newest first (DESC) by default. We want oldest first (ASC) for the chart.
    bars = await clickhouse_manager.get_bars(bare_ticker, limit=50)
    bars = list(reversed(bars))
    
    closes = [b.close for b in bars]
    chart_data = []
    
    for i, b in enumerate(bars):
        dt = b.timestamp
        # Get features if available
        feat = await duckdb_manager.get_features(bare_ticker, dt) or {}
        
        sma_5 = feat.get("sma_5")
        if sma_5 is None:
            window_5 = closes[max(0, i-4):i+1]
            sma_5 = sum(window_5) / len(window_5) if window_5 else b.close
            
        sma_20 = feat.get("sma_20")
        if sma_20 is None:
            window_20 = closes[max(0, i-19):i+1]
            sma_20 = sum(window_20) / len(window_20) if window_20 else b.close
        
        chart_data.append({
            "timestamp": dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
            "sma_5": sma_5,
            "sma_20": sma_20,
            "rsi": feat.get("rsi")
        })
        
    return chart_data


# ------------------ WebSocket Route ------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ------------------ Health & Cold Start Route ------------------

@app.get("/api/health/cold-start")
async def get_cold_start_status():
    from stock_agent.storage.integrity_checker import integrity_checker
    from stock_agent.collectors.data_seeder import data_seeder
    status = await integrity_checker.check_universe_data_health()
    status["is_seeding"] = data_seeder.is_running
    status["seeding_progress"] = data_seeder.progress
    return status

@app.post("/api/health/cold-start/trigger")
async def trigger_cold_start_seed(background_tasks: BackgroundTasks):
    from stock_agent.storage.integrity_checker import integrity_checker
    from stock_agent.collectors.data_seeder import data_seeder
    status = await integrity_checker.check_universe_data_health()
    if status["requires_bulk_update"]:
        background_tasks.add_task(data_seeder.run_bulk_seed, status["deficient_tickers"])
        return {"status": "triggered", "message": "Bulk data seeding started in the background."}
    return {"status": "ignored", "message": "No bulk update required."}

# ------------------ Frontend HTML Server ------------------

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    # 1. Try to serve compiled Vue 3 + Vite frontend from frontend/dist/index.html first
    dist_html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../frontend/dist/index.html"))
    if os.path.exists(dist_html_path):
        with open(dist_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)

    # 2. Fallback to local templates/index.html
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    else:
        return HTMLResponse(content="<h1>Index HTML not found! Run system update.</h1>", status_code=404)

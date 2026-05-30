import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from stock_agent.common.dto import Bar, Order, OrderStatus, Position, ActionType, NewsArticle
from stock_agent.common.logger import logger
from stock_agent.core.config import settings


class StorageLayer:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._keep_alive_conn = None
        self._cache: Dict[str, Any] = {}
        self._init_db()

    def use_db(self, db_url_or_path: str):
        """Switch the active database at runtime and re-initialize tables."""
        old_path = self.db_path
        if db_url_or_path.startswith("sqlite:///"):
            self.db_path = db_url_or_path.replace("sqlite:///", "")
        else:
            self.db_path = db_url_or_path
            
        if self._keep_alive_conn:
            self._keep_alive_conn.close()
            self._keep_alive_conn = None
            
        self._cache.clear()
        self._init_db()
        logger.info("StorageLayer switched active database path", old_path=old_path, new_path=self.db_path)

    def _get_connection(self):
        # We allow multiple threads to access SQLite, especially in a dev/web server context.
        path = self.db_path
        uri = False
        if path == ":memory:" or "mode=memory" in path:
            path = "file:memdb?mode=memory&cache=shared"
            uri = True
            if not self._keep_alive_conn:
                self._keep_alive_conn = sqlite3.connect(path, uri=True)
        conn = sqlite3.connect(path, check_same_thread=False, uri=uri)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        import os

        # Check if database is file-based and check file existence before connection is established
        is_memory = self.db_path == ":memory:" or "mode=memory" in self.db_path or self.db_path.startswith("file:")
        db_existed = False
        if not is_memory:
            db_existed = os.path.exists(self.db_path)

        conn = self._get_connection()
        cursor = conn.cursor()

        # TSDB - Raw Price Bars Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ts_bars (
                ticker TEXT,
                timestamp TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (ticker, timestamp)
            )
        """)

        # TSDB - Computed Features Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ts_features (
                ticker TEXT,
                timestamp TEXT,
                features TEXT, -- JSON structure
                PRIMARY KEY (ticker, timestamp)
            )
        """)

        # RDB - Orders Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rdb_orders (
                order_id TEXT PRIMARY KEY,
                ticker TEXT,
                action TEXT,
                quantity INTEGER,
                price REAL,
                status TEXT,
                timestamp TEXT,
                filled_quantity INTEGER,
                avg_fill_price REAL,
                retries INTEGER,
                reason TEXT
            )
        """)

        # RDB - Positions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rdb_positions (
                ticker TEXT PRIMARY KEY,
                quantity INTEGER,
                avg_price REAL,
                current_price REAL,
                floating_pnl REAL
            )
        """)

        # Watchlist Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                ticker TEXT PRIMARY KEY
            )
        """)

        # Raw News Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_news (
                url TEXT PRIMARY KEY,
                title TEXT,
                summary TEXT,
                source TEXT,
                published_at TEXT,
                category TEXT,
                ticker TEXT
            )
        """)

        # Raw News Table Column Migration (SQLite fallback)
        try:
            cursor.execute("PRAGMA table_info(raw_news)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "ticker" not in columns:
                cursor.execute("ALTER TABLE raw_news ADD COLUMN ticker TEXT")
                conn.commit()
        except Exception as e:
            logger.warning("Failed to migrate raw_news table schema", error=str(e))

        # Seeding defaults - only run if DB is in-memory or a newly created file DB
        if is_memory or not db_existed:
            try:
                cursor.execute("SELECT COUNT(*) as count FROM watchlist")
                row = cursor.fetchone()
                if row and row["count"] == 0:
                    universe = settings.TRADING_UNIVERSE
                    if isinstance(universe, str):
                        try:
                            universe = json.loads(universe)
                        except Exception:
                            universe = [x.strip() for x in universe.split(",") if x.strip()]
                    for t in list(universe):
                        cursor.execute("INSERT OR REPLACE INTO watchlist (ticker) VALUES (?)", (t,))
            except Exception as e:
                logger.error("Failed to seed default watchlist table", error=str(e))

        conn.commit()
        conn.close()
        logger.info("StorageLayer DB initialized successfully", db_path=self.db_path, db_existed=db_existed)

    # ------------------ TSDB: Bars ------------------

    def save_bar(self, bar: Bar):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO ts_bars (ticker, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (bar.ticker, bar.timestamp.isoformat(), bar.open, bar.high, bar.low, bar.close, bar.volume))
            conn.commit()
            # Set to real-time cache
            self.set_cache(f"latest_bar:{bar.ticker}", bar)
        except Exception as e:
            logger.error("Failed to save bar to TSDB", error=str(e), ticker=bar.ticker)
        finally:
            conn.close()

    async def save_bars(self, bars: List[Bar]):
        import asyncio
        def _save():
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                # Use executemany for bulk insert
                cursor.executemany("""
                    INSERT OR REPLACE INTO ts_bars (ticker, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [(b.ticker, b.timestamp.isoformat(), b.open, b.high, b.low, b.close, b.volume) for b in bars])
                conn.commit()
                if bars:
                    # Cache the latest bar
                    latest_bar = max(bars, key=lambda x: x.timestamp)
                    self.set_cache(f"latest_bar:{latest_bar.ticker}", latest_bar)
            except Exception as e:
                logger.error("Failed to save bars to TSDB", error=str(e), count=len(bars))
            finally:
                conn.close()
        await asyncio.to_thread(_save)

    def get_bars(
        self, 
        ticker: str, 
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_desc: bool = True
    ) -> List[Bar]:
        conn = self._get_connection()
        cursor = conn.cursor()
        bars = []
        try:
            if ticker:
                query = "SELECT ticker, timestamp, open, high, low, close, volume FROM ts_bars WHERE ticker = ?"
                params = [ticker]
            else:
                query = "SELECT ticker, timestamp, open, high, low, close, volume FROM ts_bars WHERE 1=1"
                params = []
                
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            order = "DESC" if sort_desc else "ASC"
            query += f" ORDER BY timestamp {order} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            for r in rows:
                bars.append(Bar(
                    ticker=r["ticker"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    open=r["open"],
                    high=r["high"],
                    low=r["low"],
                    close=r["close"],
                    volume=r["volume"]
                ))
        except Exception as e:
            logger.error("Failed to get bars from TSDB", error=str(e), ticker=ticker)
        finally:
            conn.close()
        return bars

    # ------------------ TSDB: Features ------------------

    def save_features(self, ticker: str, timestamp: datetime, features: Dict[str, Any]):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO ts_features (ticker, timestamp, features)
                VALUES (?, ?, ?)
            """, (ticker, timestamp.isoformat(), json.dumps(features)))
            conn.commit()
            # Cache computed features
            self.set_cache(f"latest_features:{ticker}", features)
        except Exception as e:
            logger.error("Failed to save features to TSDB", error=str(e), ticker=ticker)
        finally:
            conn.close()

    def get_features(self, ticker: str, timestamp: datetime) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        features = None
        try:
            cursor.execute("""
                SELECT features
                FROM ts_features
                WHERE ticker = ? AND timestamp = ?
            """, (ticker, timestamp.isoformat()))
            row = cursor.fetchone()
            if row:
                features = json.loads(row["features"])
        except Exception as e:
            logger.error("Failed to get features from TSDB", error=str(e), ticker=ticker)
        finally:
            conn.close()
        return features

    # ------------------ RDB: Orders ------------------

    def save_order(self, order: Order):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO rdb_orders (
                    order_id, ticker, action, quantity, price, status, timestamp,
                    filled_quantity, avg_fill_price, retries, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.ticker, order.action.value, order.quantity, order.price,
                order.status.value, order.timestamp.isoformat(), order.filled_quantity,
                order.avg_fill_price, order.retries, order.reason
            ))
            conn.commit()
        except Exception as e:
            logger.error("Failed to save order to RDB", error=str(e), order_id=order.order_id)
        finally:
            conn.close()

    def get_order(self, order_id: str) -> Optional[Order]:
        conn = self._get_connection()
        cursor = conn.cursor()
        order = None
        try:
            cursor.execute("SELECT * FROM rdb_orders WHERE order_id = ?", (order_id,))
            r = cursor.fetchone()
            if r:
                order = Order(
                    order_id=r["order_id"],
                    ticker=r["ticker"],
                    action=ActionType(r["action"]),
                    quantity=r["quantity"],
                    price=r["price"],
                    status=OrderStatus(r["status"]),
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    filled_quantity=r["filled_quantity"],
                    avg_fill_price=r["avg_fill_price"],
                    retries=r["retries"],
                    reason=r["reason"]
                )
        except Exception as e:
            logger.error("Failed to get order from RDB", error=str(e), order_id=order_id)
        finally:
            conn.close()
        return order

    def get_orders(self) -> List[Order]:
        conn = self._get_connection()
        cursor = conn.cursor()
        orders = []
        try:
            cursor.execute("SELECT * FROM rdb_orders ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            for r in rows:
                orders.append(Order(
                    order_id=r["order_id"],
                    ticker=r["ticker"],
                    action=ActionType(r["action"]),
                    quantity=r["quantity"],
                    price=r["price"],
                    status=OrderStatus(r["status"]),
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    filled_quantity=r["filled_quantity"],
                    avg_fill_price=r["avg_fill_price"],
                    retries=r["retries"],
                    reason=r["reason"]
                ))
        except Exception as e:
            logger.error("Failed to list orders from RDB", error=str(e))
        finally:
            conn.close()
        return orders

    # ------------------ RDB: Positions ------------------

    def save_position(self, position: Position):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO rdb_positions (ticker, quantity, avg_price, current_price, floating_pnl)
                VALUES (?, ?, ?, ?, ?)
            """, (position.ticker, position.quantity, position.avg_price, position.current_price, position.floating_pnl))
            conn.commit()
        except Exception as e:
            logger.error("Failed to save position to RDB", error=str(e), ticker=position.ticker)
        finally:
            conn.close()

    def delete_position(self, ticker: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM rdb_positions WHERE ticker = ?", (ticker,))
            conn.commit()
        except Exception as e:
            logger.error("Failed to delete position from RDB", error=str(e), ticker=ticker)
        finally:
            conn.close()

    def get_position(self, ticker: str) -> Optional[Position]:
        conn = self._get_connection()
        cursor = conn.cursor()
        position = None
        try:
            cursor.execute("SELECT * FROM rdb_positions WHERE ticker = ?", (ticker,))
            r = cursor.fetchone()
            if r:
                position = Position(
                    ticker=r["ticker"],
                    quantity=r["quantity"],
                    avg_price=r["avg_price"],
                    current_price=r["current_price"],
                    floating_pnl=r["floating_pnl"]
                )
        except Exception as e:
            logger.error("Failed to get position from RDB", error=str(e), ticker=ticker)
        finally:
            conn.close()
        return position

    def get_positions(self) -> List[Position]:
        conn = self._get_connection()
        cursor = conn.cursor()
        positions = []
        try:
            cursor.execute("SELECT * FROM rdb_positions")
            rows = cursor.fetchall()
            for r in rows:
                positions.append(Position(
                    ticker=r["ticker"],
                    quantity=r["quantity"],
                    avg_price=r["avg_price"],
                    current_price=r["current_price"],
                    floating_pnl=r["floating_pnl"]
                ))
        except Exception as e:
            logger.error("Failed to list positions from RDB", error=str(e))
        finally:
            conn.close()
        return positions

    # ------------------ Cache: In-memory Cache ------------------

    def set_cache(self, key: str, value: Any):
        self._cache[key] = value

    def get_cache(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def _execute_postgres_sync(self, query_str: str, params: dict = None) -> List[dict]:
        from stock_agent.infra.storage.multi_db import postgres_manager
        from sqlalchemy import text
        if not postgres_manager.active or not postgres_manager.engine:
            raise RuntimeError("Postgres not active or engine is null.")
            
        with postgres_manager.engine.connect() as conn:
            res = conn.execute(text(query_str), params or {})
            conn.commit()
            if res.returns_rows:
                return [dict(row._mapping) for row in res.all()]
        return []


    # ------------------ Watchlist ------------------

    def save_watchlist_ticker(self, ticker: str):
        from stock_agent.infra.storage.multi_db import postgres_manager
        if postgres_manager.active:
            try:
                self._execute_postgres_sync(
                    "INSERT INTO watchlist (ticker) VALUES (:ticker) ON CONFLICT (ticker) DO NOTHING",
                    {"ticker": ticker}
                )
                return
            except Exception as e:
                logger.error("Failed to save watchlist ticker to Postgres. Falling back to SQLite.", error=str(e), ticker=ticker)

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR REPLACE INTO watchlist (ticker) VALUES (?)", (ticker,))
            conn.commit()
        except Exception as e:
            logger.error("Failed to save watchlist ticker", error=str(e), ticker=ticker)
        finally:
            conn.close()

    def delete_watchlist_ticker(self, ticker: str):
        from stock_agent.infra.storage.multi_db import postgres_manager
        if postgres_manager.active:
            try:
                self._execute_postgres_sync(
                    "DELETE FROM watchlist WHERE ticker = :ticker",
                    {"ticker": ticker}
                )
                return
            except Exception as e:
                logger.error("Failed to delete watchlist ticker from Postgres. Falling back to SQLite.", error=str(e), ticker=ticker)

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
            conn.commit()
        except Exception as e:
            logger.error("Failed to delete watchlist ticker", error=str(e), ticker=ticker)
        finally:
            conn.close()

    def get_watchlist(self) -> List[str]:
        from stock_agent.infra.storage.multi_db import postgres_manager
        if postgres_manager.active:
            try:
                rows = self._execute_postgres_sync("SELECT ticker FROM watchlist")
                return [r["ticker"] for r in rows]
            except Exception as e:
                logger.error("Failed to get watchlist from Postgres. Falling back to SQLite.", error=str(e))

        conn = self._get_connection()
        cursor = conn.cursor()
        tickers = []
        try:
            cursor.execute("SELECT ticker FROM watchlist")
            rows = cursor.fetchall()
            for r in rows:
                tickers.append(r["ticker"])
        except Exception as e:
            logger.error("Failed to get watchlist from DB", error=str(e))
        finally:
            conn.close()
        return tickers

    def save_news_article(self, article: NewsArticle):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO raw_news (url, title, summary, source, published_at, category, ticker)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (article.url, article.title, article.summary, article.source, article.published_at.isoformat(), article.category, article.ticker))
            conn.commit()
        except Exception as e:
            logger.error("Failed to save news article to DB", error=str(e), url=article.url)
        finally:
            conn.close()

    def get_latest_news(
        self, 
        limit: int = 50,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        title_query: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> List[NewsArticle]:
        conn = self._get_connection()
        cursor = conn.cursor()
        articles = []
        try:
            query = "SELECT url, title, summary, source, published_at, category, ticker FROM raw_news WHERE 1=1"
            params = []
            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)
            elif category_filter:
                if category_filter == 'watchlist':
                    query += " AND ticker IS NOT NULL AND ticker != ''"
                elif category_filter == 'general':
                    query += " AND (ticker IS NULL OR ticker = '')"

            if start_date:
                query += " AND published_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND published_at <= ?"
                params.append(end_date)
            if title_query:
                query += " AND title LIKE ?"
                params.append(f"%{title_query}%")
                
            query += " ORDER BY published_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            for r in rows:
                articles.append(NewsArticle(
                     url=r["url"],
                     title=r["title"],
                     summary=r["summary"],
                     source=r["source"],
                     published_at=datetime.fromisoformat(r["published_at"]),
                     category=r["category"],
                     ticker=r["ticker"]
                ))
        except Exception as e:
            logger.error("Failed to get latest news from DB", error=str(e))
        finally:
            conn.close()
        return articles


def get_trading_universe() -> List[str]:
    """Retrieve active trading universe from DB watchlist table, falling back to settings."""
    try:
        db_list = storage_layer.get_watchlist()
        if db_list:
            return db_list
    except Exception:
        pass
    
    # Fallback
    universe = settings.TRADING_UNIVERSE
    if isinstance(universe, str):
        try:
            universe = json.loads(universe)
        except Exception:
            universe = [x.strip() for x in universe.split(",") if x.strip()]
    return list(universe)


# Global storage instance (in-memory SQLite for seamless testing and speed, which can be configured to write to file)
_db_url = settings.SQLITE_URL
if _db_url.startswith("sqlite:///"):
    _db_path = _db_url.replace("sqlite:///", "")
else:
    _db_path = "stock_agent.db"

storage_layer = StorageLayer(_db_path)

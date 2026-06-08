import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from stock_agent.core.config import settings
from stock_agent.common.logger import logger
from stock_agent.common.dto import Bar, NewsArticle

# Try to import DB libraries, providing mock fallbacks if not installed or unreachable
try:
    import sqlalchemy
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
except ImportError:
    sqlalchemy = None

try:
    import pymongo
except ImportError:
    pymongo = None

try:
    import clickhouse_connect
except ImportError:
    clickhouse_connect = None

try:
    import duckdb
except ImportError:
    duckdb = None


class PostgresManager:
    def __init__(self):
        self.active = False
        self.engine = None
        self.SessionLocal = None

    async def initialize(self):
        if not sqlalchemy or not settings.POSTGRES_URL:
            logger.warning("Postgres parameters or SQLAlchemy not found. Using SQLite fallback.")
            return

        try:
            # We use a short timeout for initial check to avoid blocking server boot
            connect_args = {"connect_timeout": 3} if "postgresql" in settings.POSTGRES_URL else {}
            self.engine = create_engine(settings.POSTGRES_URL, connect_args=connect_args)
            
            # Simple connection test and table initialization
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS watchlist (
                        ticker VARCHAR PRIMARY KEY
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS recommendations (
                        ticker VARCHAR PRIMARY KEY,
                        action VARCHAR,
                        confidence REAL,
                        rationale TEXT,
                        blackboard_state TEXT,
                        created_at VARCHAR
                    )
                """))
                conn.commit()
            
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.active = True
            logger.info("Successfully connected to PostgreSQL instance.")
        except Exception as e:
            logger.warning("PostgreSQL connection failed. Bypassing and falling back to SQLite.", error=str(e))
            self.active = False
            self.engine = None
            self.SessionLocal = None

    async def close(self):
        if self.engine:
            self.engine.dispose()
            logger.info("PostgreSQL connection pool disposed.")


class MongoManager:
    def __init__(self):
        self.active = False
        self.client = None
        self.db = None
        self.collection = None
        # Local cache fallback for mock operations
        self._mock_db: Dict[str, Any] = {}

    async def initialize(self):
        if not pymongo or not settings.MONGODB_URL:
            logger.warning("MongoDB client or MONGODB_URL not found. Using SQLite news collection fallback.")
            return

        try:
            # Set serverSelectionTimeoutMS to prevent long hangs on startup
            self.client = pymongo.MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
            # Force a connection check
            self.client.server_info()
            
            self.db = self.client.get_database("stock_agent")
            self.collection = self.db.get_collection("raw_news")
            
            # Create index for rapid url retrieval
            self.collection.create_index("url", unique=True)
            self.active = True
            logger.info("Successfully connected to MongoDB instance.")
        except Exception as e:
            logger.warning("MongoDB connection failed. Bypassing and falling back to SQLite news tables.", error=str(e))
            self.active = False
            self.client = None
            self.db = None
            self.collection = None

    async def save_news_article(self, article: NewsArticle) -> bool:
        if self.active and self.collection is not None:
            try:
                # Standardize datetime format for MongoDB
                doc = article.model_dump()
                doc["published_at"] = doc["published_at"].isoformat()
                self.collection.replace_one({"url": article.url}, doc, upsert=True)
                return True
            except Exception as e:
                logger.error("Failed to save news to MongoDB. Bypassing...", error=str(e))
        
        # Graceful Fallback: Save to SQLite raw_news table
        try:
            from stock_agent.storage.repository import storage_layer
            storage_layer.save_news_article(article)
            return True
        except Exception as ex:
            logger.error("Secondary SQLite news fallback also failed.", error=str(ex))
            return False

    async def get_latest_news(
        self, 
        limit: int = 50,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        title_query: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> List[NewsArticle]:
        if self.active and self.collection is not None:
            try:
                query_dict = {}
                if ticker:
                    query_dict["ticker"] = ticker
                elif category_filter:
                    if category_filter == 'watchlist':
                        query_dict["ticker"] = {"$ne": None, "$nin": [None, ""]}
                    elif category_filter == 'general':
                        query_dict["ticker"] = {"$in": [None, ""]}

                if start_date or end_date:
                    published_at_query = {}
                    if start_date:
                        published_at_query["$gte"] = start_date
                    if end_date:
                        published_at_query["$lte"] = end_date
                    query_dict["published_at"] = published_at_query
                if title_query:
                    query_dict["title"] = {"$regex": title_query, "$options": "i"}
                    
                docs = list(self.collection.find(query_dict).sort("published_at", pymongo.DESCENDING).limit(limit))
                articles = []
                for d in docs:
                    published_at = d["published_at"]
                    if isinstance(published_at, str):
                        published_at = datetime.fromisoformat(published_at)
                    articles.append(NewsArticle(
                        url=d["url"],
                        title=d["title"],
                        summary=d["summary"],
                        source=d["source"],
                        published_at=published_at,
                        category=d.get("category", "finance_economics"),
                        ticker=d.get("ticker")
                    ))
                return articles
            except Exception as e:
                logger.error("Failed to query MongoDB. Bypassing to SQLite...", error=str(e))

        # Graceful Fallback: Query from SQLite raw_news table
        try:
            from stock_agent.storage.repository import storage_layer
            return storage_layer.get_latest_news(
                limit=limit,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                title_query=title_query,
                category_filter=category_filter
            )
        except Exception:
            return []

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB client connections closed.")


class ClickHouseManager:
    def __init__(self):
        self.active = False
        self.client = None

    async def initialize(self):
        if not clickhouse_connect or not settings.CLICKHOUSE_URL:
            logger.warning("ClickHouse client or CLICKHOUSE_URL not found. Using SQLite ts_bars fallback.")
            return

        try:
            # Parse settings
            # e.g., clickhouse://username:password@host:port/database
            # We simplify connection for robustness
            host = "localhost"
            port = 8123
            username = "default"
            password = ""
            database = "default"
            
            # Basic parsing if present
            url = settings.CLICKHOUSE_URL
            if "://" in url:
                parsed = url.split("://")[1]
                if "@" in parsed:
                    credentials, host_db = parsed.split("@")
                    if ":" in credentials:
                        username, password = credentials.split(":")
                else:
                    host_db = parsed
                
                if "/" in host_db:
                    host_port, database = host_db.split("/")
                else:
                    host_port = host_db
                
                if ":" in host_port:
                    host, port_str = host_port.split(":")
                    port = int(port_str)
                else:
                    host = host_port

            self.client = clickhouse_connect.get_client(
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
                connect_timeout=2
            )
            
            # Create schema if not exists
            self.client.command("""
                CREATE TABLE IF NOT EXISTS bars (
                    ticker String,
                    timestamp DateTime,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume Float64
                ) ENGINE = MergeTree()
                ORDER BY (ticker, timestamp)
            """)
            self.active = True
            logger.info("Successfully connected to ClickHouse instance.")
        except Exception as e:
            logger.warning("ClickHouse connection failed. Bypassing and falling back to SQLite ts_bars.", error=str(e))
            self.active = False
            self.client = None

    async def save_bar(self, bar: Bar) -> bool:
        if self.active and self.client is not None:
            try:
                data = [[
                    bar.ticker,
                    bar.timestamp,
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume
                ]]
                self.client.insert("bars", data, column_names=["ticker", "timestamp", "open", "high", "low", "close", "volume"])
                return True
            except Exception as e:
                logger.error("Failed to insert bar to ClickHouse. Bypassing to SQLite...", error=str(e))

        # Graceful Fallback: Save to SQLite ts_bars table
        try:
            from stock_agent.storage.repository import storage_layer
            storage_layer.save_bar(bar)
            return True
        except Exception as ex:
            logger.error("Secondary SQLite ts_bars fallback also failed.", error=str(ex))
            return False

    async def get_bars(
        self, 
        ticker: Optional[str] = None, 
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_desc: bool = True
    ) -> List[Bar]:
        if self.active and self.client is not None:
            try:
                # Query in ClickHouse
                if ticker:
                    query = "SELECT ticker, timestamp, open, high, low, close, volume FROM bars WHERE ticker = %(ticker)s"
                    params = {"ticker": ticker, "limit": limit, "offset": offset}
                else:
                    query = "SELECT ticker, timestamp, open, high, low, close, volume FROM bars WHERE 1=1"
                    params = {"limit": limit, "offset": offset}
                
                if start_date:
                    query += " AND timestamp >= %(start_date)s"
                    params["start_date"] = start_date
                if end_date:
                    query += " AND timestamp <= %(end_date)s"
                    params["end_date"] = end_date
                    
                order = "DESC" if sort_desc else "ASC"
                query += f" ORDER BY timestamp {order} LIMIT %(limit)s OFFSET %(offset)s"
                
                result = self.client.query(query, parameters=params)
                bars = []
                for row in result.result_rows:
                    bars.append(Bar(
                        ticker=row[0],
                        timestamp=row[1],
                        open=row[2],
                        high=row[3],
                        low=row[4],
                        close=row[5],
                        volume=row[6]
                    ))
                return bars
            except Exception as e:
                logger.error("Failed to query ClickHouse. Bypassing to SQLite...", error=str(e))

        # Graceful Fallback: Query from SQLite ts_bars table
        try:
            from stock_agent.storage.repository import storage_layer
            return storage_layer.get_bars(ticker, limit, offset, start_date, end_date, sort_desc)
        except Exception:
            return []

    async def close(self):
        if self.client:
            # clickhouse_connect doesn't have an explicit close, but we release reference
            self.client = None
            logger.info("ClickHouse client connection released.")


class DuckDBManager:
    def __init__(self):
        self.active = False
        self.conn = None

    async def initialize(self):
        if not duckdb:
            logger.warning("DuckDB package not found. Using local JSON dict analytical fallback.")
            return

        try:
            # We connect/create a local in-process duckdb file-based database
            db_path = settings.DUCKDB_PATH
            self.conn = duckdb.connect(db_path)
            
            # Setup features table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS computed_features (
                    ticker VARCHAR,
                    timestamp TIMESTAMP,
                    features JSON,
                    PRIMARY KEY (ticker, timestamp)
                )
            """)
            self.active = True
            logger.info("Successfully initialized DuckDB embedded engine.", path=db_path)
        except Exception as e:
            logger.warning("Failed to initialize DuckDB. Using local memory mock cache.", error=str(e))
            self.active = False
            self.conn = None

    async def save_features(self, ticker: str, timestamp: datetime, features: Dict[str, Any]) -> bool:
        if self.active and self.conn is not None:
            try:
                features_json = json.dumps(features)
                # Insert or update
                self.conn.execute("""
                    INSERT OR REPLACE INTO computed_features (ticker, timestamp, features)
                    VALUES (?, ?, ?)
                """, (ticker, timestamp, features_json))
                return True
            except Exception as e:
                logger.error("Failed to save features to DuckDB. Bypassing...", error=str(e))

        # Fallback to saving in SQLite ts_features
        try:
            from stock_agent.storage.repository import storage_layer
            storage_layer.save_features(ticker, timestamp, features)
            return True
        except Exception as ex:
            logger.error("Secondary SQLite features fallback also failed.", error=str(ex))
            return False

    async def get_features(self, ticker: str, timestamp: datetime) -> Optional[Dict[str, Any]]:
        if self.active and self.conn is not None:
            try:
                res = self.conn.execute("""
                    SELECT features FROM computed_features
                    WHERE ticker = ? AND timestamp = ?
                """, (ticker, timestamp)).fetchone()
                if res:
                    return json.loads(res[0])
            except Exception as e:
                logger.error("Failed to query features from DuckDB. Bypassing...", error=str(e))

        # Fallback to querying SQLite ts_features
        try:
            from stock_agent.storage.repository import storage_layer
            return storage_layer.get_features(ticker, timestamp)
        except Exception:
            return None

    async def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("DuckDB connection closed cleanly.")


# Global singleton instances for all 4 databases
postgres_manager = PostgresManager()
mongo_manager = MongoManager()
clickhouse_manager = ClickHouseManager()
duckdb_manager = DuckDBManager()


async def initialize_all_dbs():
    """Initializes connections for Postgres, MongoDB, ClickHouse, and DuckDB in sequence."""
    logger.info("Initializing multi-database client infrastructure...")
    await postgres_manager.initialize()
    await mongo_manager.initialize()
    await clickhouse_manager.initialize()
    await duckdb_manager.initialize()
    logger.info("Multi-database client infrastructure initialization completed.")


async def close_all_dbs():
    """Closes all database connections cleanly on system shutdown."""
    logger.info("Closing multi-database client connections...")
    await postgres_manager.close()
    await mongo_manager.close()
    await clickhouse_manager.close()
    await duckdb_manager.close()
    logger.info("All multi-database connections closed successfully.")

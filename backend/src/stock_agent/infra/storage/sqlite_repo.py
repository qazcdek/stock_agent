import json
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, UniqueConstraint, desc
from sqlalchemy.orm import declarative_base, sessionmaker
from stock_agent.core.config import settings
from stock_agent.core.enums import OrderStatus, Action, OrderType
from stock_agent.core.schemas import Bar, Signal, Order, Position, PortfolioState, NewsArticle
from stock_agent.core.interfaces import DataRepository

Base = declarative_base()

class BarModel(Base):
    __tablename__ = "bars"
    ticker = Column(String, primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)


class SignalModel(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False)
    action = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    rationale = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class OrderModel(Base):
    __tablename__ = "orders"
    order_id = Column(String, primary_key=True)
    ticker = Column(String, nullable=False)
    action = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)


class PortfolioStateModel(Base):
    __tablename__ = "portfolio_states"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cash = Column(Float, nullable=False)
    total_asset = Column(Float, nullable=False)
    positions_json = Column(String, nullable=False)  # JSON-serialized Dict[str, Position]
    timestamp = Column(DateTime, default=datetime.utcnow)


class WatchlistModel(Base):
    __tablename__ = "watchlist"
    ticker = Column(String, primary_key=True)


class NewsArticleModel(Base):
    __tablename__ = "raw_news"
    url = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    source = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)
    category = Column(String, nullable=False, default="finance_economics")


class SQLiteRepository(DataRepository):
    def __init__(self, db_url: str = settings.SQLITE_URL):
        # Allow sqlite in-memory or file databases. Ensure thread compatibility for SQLite.
        from stock_agent.infra.storage.multi_db import postgres_manager
        from stock_agent.common.logger import logger
        
        if postgres_manager.active and db_url == settings.SQLITE_URL:
            logger.info("SQLiteRepository routing transactions dynamically to PostgreSQL pool.")
            self.engine = postgres_manager.engine
            Base.metadata.create_all(self.engine)
            self.SessionLocal = postgres_manager.SessionLocal
        else:
            connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
            self.engine = create_engine(db_url, connect_args=connect_args)
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    async def save_bars(self, bars: List[Bar]) -> None:
        with self.SessionLocal() as session:
            for bar in bars:
                # Upsert logic for SQLite
                db_bar = session.query(BarModel).filter_by(ticker=bar.ticker, timestamp=bar.timestamp).first()
                if db_bar:
                    db_bar.open = bar.open
                    db_bar.high = bar.high
                    db_bar.low = bar.low
                    db_bar.close = bar.close
                    db_bar.volume = bar.volume
                else:
                    db_bar = BarModel(
                        ticker=bar.ticker,
                        timestamp=bar.timestamp,
                        open=bar.open,
                        high=bar.high,
                        low=bar.low,
                        close=bar.close,
                        volume=bar.volume
                    )
                    session.add(db_bar)
            session.commit()

    async def get_bars(self, ticker: str, start_dt: datetime, end_dt: datetime) -> List[Bar]:
        with self.SessionLocal() as session:
            db_bars = session.query(BarModel).filter(
                BarModel.ticker == ticker,
                BarModel.timestamp >= start_dt,
                BarModel.timestamp <= end_dt
            ).order_by(BarModel.timestamp.asc()).all()
            
            return [
                Bar(
                    ticker=b.ticker,
                    timestamp=b.timestamp,
                    open=b.open,
                    high=b.high,
                    low=b.low,
                    close=b.close,
                    volume=b.volume
                ) for b in db_bars
            ]

    async def save_signal(self, signal: Signal) -> None:
        with self.SessionLocal() as session:
            db_signal = SignalModel(
                ticker=signal.ticker,
                action=signal.action.value,
                confidence=signal.confidence,
                rationale=signal.rationale,
                timestamp=signal.timestamp
            )
            session.add(db_signal)
            session.commit()

    async def get_signals(self, ticker: Optional[str] = None, limit: int = 100) -> List[Signal]:
        with self.SessionLocal() as session:
            query = session.query(SignalModel)
            if ticker:
                query = query.filter(SignalModel.ticker == ticker)
            db_signals = query.order_by(desc(SignalModel.timestamp)).limit(limit).all()
            
            return [
                Signal(
                    ticker=s.ticker,
                    action=Action(s.action),
                    confidence=s.confidence,
                    rationale=s.rationale,
                    timestamp=s.timestamp
                ) for s in db_signals
            ]

    async def save_order(self, order: Order) -> None:
        with self.SessionLocal() as session:
            db_order = OrderModel(
                order_id=order.order_id,
                ticker=order.ticker,
                action=order.action.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
                price=order.price,
                status=order.status.value,
                created_at=order.created_at,
                filled_at=order.filled_at
            )
            session.merge(db_order)
            session.commit()

    async def get_orders(self, ticker: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Order]:
        with self.SessionLocal() as session:
            query = session.query(OrderModel)
            if ticker:
                query = query.filter(OrderModel.ticker == ticker)
            if status:
                query = query.filter(OrderModel.status == status.value)
            db_orders = query.order_by(desc(OrderModel.created_at)).all()
            
            return [
                Order(
                    order_id=o.order_id,
                    ticker=o.ticker,
                    action=Action(o.action),
                    order_type=OrderType(o.order_type),
                    quantity=o.quantity,
                    price=o.price,
                    status=OrderStatus(o.status),
                    created_at=o.created_at,
                    filled_at=o.filled_at
                ) for o in db_orders
            ]

    async def update_order(self, order_id: str, status: OrderStatus, filled_at: Optional[datetime] = None) -> Optional[Order]:
        with self.SessionLocal() as session:
            db_order = session.query(OrderModel).filter(OrderModel.order_id == order_id).first()
            if not db_order:
                return None
            db_order.status = status.value
            if filled_at:
                db_order.filled_at = filled_at
            session.commit()
            return Order(
                order_id=db_order.order_id,
                ticker=db_order.ticker,
                action=Action(db_order.action),
                order_type=OrderType(db_order.order_type),
                quantity=db_order.quantity,
                price=db_order.price,
                status=OrderStatus(db_order.status),
                created_at=db_order.created_at,
                filled_at=db_order.filled_at
            )

    async def save_portfolio_state(self, state: PortfolioState) -> None:
        with self.SessionLocal() as session:
            # Serialize positions to dict for JSON serialization
            serialized_positions = {
                ticker: pos.model_dump(mode="json")
                for ticker, pos in state.positions.items()
            }
            db_state = PortfolioStateModel(
                cash=state.cash,
                total_asset=state.total_asset,
                positions_json=json.dumps(serialized_positions),
                timestamp=state.timestamp
            )
            session.add(db_state)
            session.commit()

    async def get_latest_portfolio_state(self) -> Optional[PortfolioState]:
        with self.SessionLocal() as session:
            db_state = session.query(PortfolioStateModel).order_by(desc(PortfolioStateModel.timestamp)).first()
            if not db_state:
                return None
            
            raw_positions = json.loads(db_state.positions_json)
            positions = {
                ticker: Position(**pos_data)
                for ticker, pos_data in raw_positions.items()
            }
            
            return PortfolioState(
                cash=db_state.cash,
                total_asset=db_state.total_asset,
                positions=positions,
                timestamp=db_state.timestamp
            )

    async def get_watchlist(self) -> List[str]:
        with self.SessionLocal() as session:
            db_tickers = session.query(WatchlistModel).all()
            return [w.ticker for w in db_tickers]

    async def add_watchlist_ticker(self, ticker: str) -> None:
        with self.SessionLocal() as session:
            db_ticker = session.query(WatchlistModel).filter_by(ticker=ticker).first()
            if not db_ticker:
                db_ticker = WatchlistModel(ticker=ticker)
                session.add(db_ticker)
                session.commit()

    async def remove_watchlist_ticker(self, ticker: str) -> None:
        with self.SessionLocal() as session:
            db_ticker = session.query(WatchlistModel).filter_by(ticker=ticker).first()
            if db_ticker:
                session.delete(db_ticker)
                session.commit()

    async def save_news_article(self, article: NewsArticle) -> None:
        with self.SessionLocal() as session:
            db_article = session.query(NewsArticleModel).filter_by(url=article.url).first()
            if db_article:
                db_article.title = article.title
                db_article.summary = article.summary
                db_article.source = article.source
                db_article.published_at = article.published_at
                db_article.category = article.category
            else:
                db_article = NewsArticleModel(
                    url=article.url,
                    title=article.title,
                    summary=article.summary,
                    source=article.source,
                    published_at=article.published_at,
                    category=article.category
                )
                session.add(db_article)
            session.commit()

    async def get_latest_news(self, limit: int = 50) -> List[NewsArticle]:
        with self.SessionLocal() as session:
            db_articles = session.query(NewsArticleModel).order_by(desc(NewsArticleModel.published_at)).limit(limit).all()
            return [
                NewsArticle(
                    url=a.url,
                    title=a.title,
                    summary=a.summary,
                    source=a.source,
                    published_at=a.published_at,
                    category=a.category
                ) for a in db_articles
            ]

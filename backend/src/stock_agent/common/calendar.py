import pytz
from datetime import datetime, time, date, timedelta
from enum import Enum

class Market(Enum):
    KOSPI = "KOSPI"
    US = "US"
    CRYPTO = "CRYPTO"

class TradingCalendar:
    def __init__(self):
        self.tz_seoul = pytz.timezone('Asia/Seoul')
        self.tz_ny = pytz.timezone('US/Eastern')
        self.tz_utc = pytz.utc

    def is_market_open(self, market: Market, dt: datetime = None) -> bool:
        if dt is None:
            dt = datetime.now(self.tz_utc)
        
        # Ensure dt is timezone aware. If naive, assume UTC.
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)

        if market == Market.CRYPTO:
            return True  # 24/7

        elif market == Market.KOSPI:
            # Convert to KST
            dt_kst = dt.astimezone(self.tz_seoul)
            # Mon(0) to Fri(4)
            if dt_kst.weekday() > 4:
                return False
            # 09:00 to 15:30 KST
            open_time = time(9, 0)
            close_time = time(15, 30)
            return open_time <= dt_kst.time() <= close_time

        elif market == Market.US:
            # Convert to Eastern Time (handles DST automatically)
            dt_est = dt.astimezone(self.tz_ny)
            if dt_est.weekday() > 4:
                return False
            # 09:30 to 16:00 ET
            open_time = time(9, 30)
            close_time = time(16, 0)
            return open_time <= dt_est.time() <= close_time

        return False

    def get_market_close_time(self, market: Market, target_date: date) -> datetime:
        """Returns the market close time (timezone aware) for the given date and market."""
        if market == Market.CRYPTO:
            # Crypto "daily close" is typically UTC 00:00 (which means end of the given day, or start of next day)
            dt = datetime.combine(target_date + timedelta(days=1), time(0, 0))
            return self.tz_utc.localize(dt)
            
        elif market == Market.KOSPI:
            dt = datetime.combine(target_date, time(15, 30))
            return self.tz_seoul.localize(dt)
            
        elif market == Market.US:
            dt = datetime.combine(target_date, time(16, 0))
            return self.tz_ny.localize(dt)
            
        raise ValueError(f"Unknown market: {market}")

# Global singleton
trading_calendar = TradingCalendar()

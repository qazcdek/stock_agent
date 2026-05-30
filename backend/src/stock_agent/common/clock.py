import asyncio
from datetime import datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current time."""
        ...
        
    async def sleep(self, seconds: float) -> None:
        """Sleep for a given number of seconds."""
        ...


class RealTimeClock(Clock):
    def now(self) -> datetime:
        return datetime.now()
        
    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class VirtualClock(Clock):
    def __init__(self, start_time: datetime):
        self._current_time = start_time

    def now(self) -> datetime:
        return self._current_time

    def set_time(self, new_time: datetime):
        self._current_time = new_time

    def advance_by(self, delta):
        self._current_time += delta
        
    async def sleep(self, seconds: float) -> None:
        # Simplified for VirtualClock without backtest engine interaction
        self.advance_by(timedelta(seconds=seconds))
        await asyncio.sleep(0)


class SimulationClock(Clock):
    """백테스팅용. 외부에서 시간을 진행시킴."""
    def __init__(self, start: datetime):
        self._time = start
        self._sleepers: list[tuple[datetime, asyncio.Future]] = []

    def now(self) -> datetime:
        return self._time

    async def sleep(self, seconds: float) -> None:
        target = self._time + timedelta(seconds=seconds)
        fut = asyncio.get_event_loop().create_future()
        self._sleepers.append((target, fut))
        await fut

    def advance_to(self, t: datetime) -> None:
        """백테스트 엔진이 시간을 앞으로 진행."""
        self._time = t
        # 만료된 sleep들을 깨움
        remaining = []
        for target, fut in self._sleepers:
            if target <= self._time:
                if not fut.done():
                    fut.set_result(None)
            else:
                remaining.append((target, fut))
        self._sleepers = remaining

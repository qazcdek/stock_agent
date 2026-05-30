import asyncio
from typing import Callable, Dict, List, Union, Awaitable, Protocol
from stock_agent.common.dto import Event
from stock_agent.common.logger import logger
import collections


HandlerType = Union[Callable[[Event], None], Callable[[Event], Awaitable[None]]]


class EventBus(Protocol):
    async def publish(self, event: Event) -> None:
        """Pub/Sub: 여러 구독자에게 브로드캐스트 (Fire-and-forget)"""
        ...

    def subscribe(self, event_type: str, handler: HandlerType) -> None:
        """Pub/Sub: 특정 토픽의 이벤트를 수신"""
        ...

    async def send(self, queue_name: str, event: Event) -> None:
        """Queue: 1명의 소비자(Worker)에게만 전달"""
        ...

    def receive(self, queue_name: str, handler: HandlerType) -> None:
        """Queue: Worker로서 큐에서 이벤트를 소비"""
        ...


class MemoryEventBus:
    def __init__(self):
        self._handlers: Dict[str, List[HandlerType]] = collections.defaultdict(list)
        self._queues: Dict[str, asyncio.Queue] = collections.defaultdict(asyncio.Queue)
        self._queue_handlers: Dict[str, HandlerType] = {}
        self._queue_tasks: List[asyncio.Task] = []

    def subscribe(self, event_type: str, handler: HandlerType):
        self._handlers[event_type].append(handler)
        logger.debug("EventBus subscribed handler", event_type=event_type, handler=handler.__name__ if hasattr(handler, "__name__") else str(handler))

    async def publish(self, event: Event):
        logger.info("EventBus publishing event", event_type=event.event_type, event_id=event.event_id)
        
        # Match explicit event_type or catch-all "*"
        handlers = self._handlers.get(event.event_type, []).copy()
        handlers.extend(self._handlers.get("*", []).copy())
        
        if not handlers:
            logger.debug("No handlers found for event", event_type=event.event_type)
            return

        tasks = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(event)))
                else:
                    handler(event)
            except Exception as e:
                logger.error("Error executing sync event handler", event_type=event.event_type, handler=str(handler), error=str(e))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res, handler in zip(results, [t for t in handlers if asyncio.iscoroutinefunction(t)]):
                if isinstance(res, Exception):
                    logger.error("Error executing async event handler", event_type=event.event_type, handler=str(handler), error=str(res))

    async def send(self, queue_name: str, event: Event) -> None:
        """Send an event to a specific queue (Worker pattern)."""
        logger.info("EventBus sending event to queue", queue_name=queue_name, event_type=event.event_type, event_id=event.event_id)
        await self._queues[queue_name].put(event)

    def receive(self, queue_name: str, handler: HandlerType) -> None:
        """Register a handler to consume from a queue (Worker pattern)."""
        if queue_name in self._queue_handlers:
            logger.warning(f"Handler already registered for queue {queue_name}. Overwriting.")
        self._queue_handlers[queue_name] = handler
        
        # Start a background task to process the queue
        task = asyncio.create_task(self._process_queue(queue_name))
        self._queue_tasks.append(task)
        logger.debug("EventBus queue receiver registered", queue_name=queue_name, handler=handler.__name__ if hasattr(handler, "__name__") else str(handler))

    async def _process_queue(self, queue_name: str):
        queue = self._queues[queue_name]
        while True:
            try:
                event = await queue.get()
                handler = self._queue_handlers.get(queue_name)
                if not handler:
                    queue.task_done()
                    continue
                
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error("Error executing queue handler", queue_name=queue_name, handler=str(handler), error=str(e))
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error processing queue", queue_name=queue_name, error=str(e))


# Global EventBus Instance
event_bus: EventBus = MemoryEventBus()

import logging
import sys
from typing import Any, Dict
import structlog


def setup_logger(name: str = "stock_agent", level: str = "INFO") -> structlog.BoundLogger:
    """Configures structured logging using structlog."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if sys.stdout.isatty() is False else structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure python standard logging to route through structlog if needed
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO)
    )
    
    return structlog.get_logger(name)


# Shared logger instance
logger = setup_logger()

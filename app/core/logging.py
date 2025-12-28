"""Structured JSON logging for CloudWatch compatibility."""
import logging
import json
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional
from datetime import datetime, timezone

# Context variables for request-scoped data
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


def set_context(**kwargs) -> None:
    """Set context variables for the current request/conversation."""
    ctx = request_context.get().copy()
    ctx.update(kwargs)
    request_context.set(ctx)


def clear_context() -> None:
    """Clear context at end of request."""
    request_context.set({})


def get_context() -> Dict[str, Any]:
    """Get current context."""
    return request_context.get()


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context from ContextVar
        ctx = request_context.get()
        if ctx:
            log_data["context"] = ctx

        # Add extra fields passed to logger
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName
        }

        return json.dumps(log_data, default=str)


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that includes context and extra fields."""

    def process(self, msg, kwargs):
        # Merge extra fields
        extra = kwargs.get('extra', {})
        extra['extra_fields'] = {**self.extra, **extra}
        kwargs['extra'] = extra
        return msg, kwargs


def get_logger(name: str, **default_fields) -> ContextLogger:
    """Get a logger with optional default fields.

    Args:
        name: Logger name (usually __name__)
        **default_fields: Fields to include in every log from this logger

    Returns:
        ContextLogger with JSON formatting

    Example:
        logger = get_logger(__name__, agent="scout")
        logger.info("Query received", extra={"query": "test"})
    """
    logger = logging.getLogger(name)
    return ContextLogger(logger, default_fields)


def setup_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure root logger.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_output: If True, use JSON format. If False, use simple format.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)

    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        # Human-readable format for local dev
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    root_logger.addHandler(handler)

"""Structured logging framework.

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Resume parsed", resume_id="abc", pages=3)
"""

import json
import logging
import sys
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from datetime import datetime, timezone

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_request_id(rid: str) -> None:
    _request_id.set(rid)


def get_request_id() -> str:
    return _request_id.get()


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


def generate_request_id() -> str:
    return uuid.uuid4().hex[:16]


class StructuredFormatter(logging.Formatter):
    """JSON log formatter for production, pretty for development."""

    def __init__(self, fmt: str | None = None, *, json_mode: bool = False):
        super().__init__(fmt)
        self.json_mode = json_mode

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
        }

        if hasattr(record, "extra_fields"):
            base.update(record.extra_fields)

        if record.exc_info and record.exc_info[0]:
            base["exception"] = self.formatException(record.exc_info)

        if self.json_mode:
            return json.dumps(base, default=str)
        else:
            ts = base.pop("timestamp")[11:19]
            rid = base.pop("request_id", "")[:8]
            level = base.pop("level", "INFO").ljust(5)
            logger_name = base.pop("logger", "").split(".")[-1].ljust(16)
            msg = base.pop("message", "")
            extras = " ".join(f"{k}={v}" for k, v in base.items() if k not in ("correlation_id",))
            return f"{ts} {rid} {level} {logger_name} {msg} {extras}".strip()


class StructuredLogger(logging.Logger):
    """Logger that accepts extra fields."""

    def _log(self, level, msg, args, exc_info=None, extra=None, **kwargs):
        if extra is None:
            extra = {}
        if kwargs:
            extra["extra_fields"] = kwargs
        super()._log(level, msg, args, exc_info=exc_info, extra=extra)


logging.setLoggerClass(StructuredLogger)


def get_logger(name: str) -> StructuredLogger:
    logger = logging.getLogger(name)
    return logger  # type: ignore


def setup_logging(*, json_mode: bool = False, level: int = logging.INFO) -> None:
    formatter = StructuredFormatter(json_mode=json_mode)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("fitz").setLevel(logging.WARNING)

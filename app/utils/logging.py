"""Structured logging helper with request-aware JSON payloads."""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key in ("request_id", "user_id", "organization_id", "path"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        return json.dumps(payload, default=str)


class JsonLogger(logging.Logger):
    def addHandler(self, handler: logging.Handler) -> None:
        super().addHandler(handler)
        if not isinstance(handler.formatter, JsonFormatter):
            handler.setFormatter(JsonFormatter())


logging.setLoggerClass(JsonLogger)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler(sys.stdout))

    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    return logger

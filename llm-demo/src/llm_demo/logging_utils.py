"""Structured logging helpers for llm-demo."""
from __future__ import annotations

import json
import logging
from logging import Logger
from pathlib import Path
from typing import Any, Dict


class JsonFileHandler(logging.Handler):
    """Write log records as JSON lines."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a", encoding="utf-8")

    def emit(self, record: logging.LogRecord) -> None:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "time": getattr(record, "asctime", None),
            "extra": getattr(record, "extra", {}),
        }
        self._stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()
        super().close()


def configure_logger(name: str, *, file_path: Path | None = None) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if file_path is not None:
        file_handler = JsonFileHandler(file_path)
        logger.addHandler(file_handler)

    return logger

"""Logging utilities for the DomainDetermine CLI."""

from __future__ import annotations

import logging
import logging.config
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

LOGGER_NAME = "DomainDetermine.cli"


def configure_logging(log_path: Path, log_format: str, verbose: bool) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers: dict[str, dict[str, object]] = {
        "file": {
            "class": "logging.FileHandler",
            "filename": str(log_path),
            "mode": "a",
            "encoding": "utf-8",
            "formatter": "json" if log_format == "json" else "text",
        }
    }

    formatters = {
        "text": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    }

    console_handler = {
        "class": "logging.StreamHandler",
        "stream": sys.stdout,
        "formatter": "json" if log_format == "json" else "text",
        "level": "DEBUG" if verbose else "INFO",
    }
    handlers["console"] = console_handler

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatters,
            "handlers": handlers,
            "loggers": {
                LOGGER_NAME: {
                    "handlers": ["console", "file"],
                    "level": "DEBUG" if verbose else "INFO",
                    "propagate": False,
                }
            },
            "root": {
                "level": "DEBUG" if verbose else "INFO",
                "handlers": list(handlers.keys()),
            },
        }
    )
    logger = logging.getLogger(LOGGER_NAME)
    logger.debug("Logging configured", extra={"log_path": str(log_path), "log_format": log_format})
    return logger


@contextmanager
def progress_spinner(message: str) -> Iterator[Progress]:
    console = Console(stderr=True)
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        transient=True,
        console=console,
    )
    task_id = progress.add_task(message)
    with progress:
        yield progress
    progress.update(task_id, completed=1)



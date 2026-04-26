"""
Application logging helpers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from config.settings import APP_NAME


def default_log_dir() -> Path:
    return Path.cwd() / "logs"


@dataclass
class OperationLogger:
    name: str
    operation_id: str
    log_path: Path
    logger: logging.Logger

    def info(self, message: str) -> None:
        self.logger.info(message)

    def error(self, message: str) -> None:
        self.logger.error(message)


def create_operation_logger(name: str, log_dir: Path | None = None) -> OperationLogger:
    operation_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    log_root = log_dir or default_log_dir()
    log_root.mkdir(parents=True, exist_ok=True)
    log_path = log_root / f"{name}-{operation_id}.log"

    logger_name = f"{APP_NAME}.{name}.{operation_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logger.addHandler(handler)

    logger.info("operation started: %s", operation_id)
    return OperationLogger(name=name, operation_id=operation_id, log_path=log_path, logger=logger)

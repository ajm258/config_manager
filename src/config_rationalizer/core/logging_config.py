import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """Structured application audit logger."""

    def __init__(self, logger: logging.Logger, run_id: str | None = None):
        self.logger = logger
        self.run_id = run_id

    def event(
        self,
        event: str,
        *,
        level: int = logging.INFO,
        **details: Any,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "run_id": self.run_id,
            "details": details,
        }

        self.logger.log(level, json.dumps(record, default=str, sort_keys=True))


def configure_logging(
    *,
    level: str = "INFO",
    log_file: Path | None = None,
    console: bool = True,
) -> AuditLogger:
    logger = logging.getLogger("config_rationalizer")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(message)s")

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return AuditLogger(logger)
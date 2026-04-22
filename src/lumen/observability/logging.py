"""JSON-friendly structured logging — extended with trace correlation in week 3."""

from __future__ import annotations

import logging
import sys

from lumen.config import get_settings


def configure_logging() -> None:
    level = getattr(logging, get_settings().lumen_log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

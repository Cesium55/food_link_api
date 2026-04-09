"""Backward-compatible wrapper around the project logger."""

from logger import get_logger


_logger = get_logger("debug_logger")


def log_debug(message: str, prefix: str = "DEBUG") -> None:
    _logger.info(message, extra={"stage": prefix})

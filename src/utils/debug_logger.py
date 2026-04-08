"""Backward-compatible wrapper around the project logger."""

from logger import get_sync_logger


_logger = get_sync_logger("debug_logger")


def hard_log(message: str, prefix: str = "DEBUG") -> None:
    _logger.info(message, extra={"stage": prefix})

import asyncio
import atexit
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Optional

from config import settings


class Logger:
    """File logger with a sync API and optional async background writes."""

    def __init__(self, name: str, log_file: str, async_mode: bool) -> None:
        self.name = name
        self.log_file = log_file
        self.async_mode = async_mode
        self._log_level = getattr(settings, "log_level", "INFO").upper()
        self._pending_lines: Deque[str] = deque()
        self._write_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._drain_task: asyncio.Task | None = None
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    def _format_line(self, level: str, message: str, extra: Optional[dict] = None) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - {self.name} - {level} - {message}"
        if extra:
            log_message += f" - {extra}"
        return f"{log_message}\n"

    def _write_line_sync(self, line: str) -> None:
        try:
            with self._write_lock:
                with open(self.log_file, "a", encoding="utf-8") as file:
                    file.write(line)
        except Exception as exc:
            print(f"Error writing log line: {exc}")

    async def _drain_pending_lines(self) -> None:
        try:
            while True:
                with self._state_lock:
                    if not self._pending_lines:
                        self._drain_task = None
                        return
                    line = self._pending_lines.popleft()
                await asyncio.to_thread(self._write_line_sync, line)
        except Exception as exc:
            print(f"Error in async logger task: {exc}")
            self.flush()
            with self._state_lock:
                self._drain_task = None

    def _ensure_async_drain_task(self) -> None:
        if not self.async_mode:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.flush()
            return

        with self._state_lock:
            if self._drain_task is None or self._drain_task.done():
                self._drain_task = loop.create_task(self._drain_pending_lines())

    def _log(self, level: str, message: str, extra: Optional[dict] = None) -> None:
        line = self._format_line(level, message, extra)

        if not self.async_mode:
            self._write_line_sync(line)
            return

        with self._state_lock:
            self._pending_lines.append(line)

        self._ensure_async_drain_task()

    def flush(self) -> None:
        while True:
            with self._state_lock:
                if not self._pending_lines:
                    return
                line = self._pending_lines.popleft()
            self._write_line_sync(line)

    def close(self) -> None:
        self.flush()

    def debug(self, message: str, extra: Optional[dict] = None) -> None:
        self._log("DEBUG", message, extra)

    def info(self, message: str, extra: Optional[dict] = None) -> None:
        self._log("INFO", message, extra)

    def warning(self, message: str, extra: Optional[dict] = None) -> None:
        self._log("WARNING", message, extra)

    def error(self, message: str, extra: Optional[dict] = None) -> None:
        self._log("ERROR", message, extra)

    def critical(self, message: str, extra: Optional[dict] = None) -> None:
        self._log("CRITICAL", message, extra)


_loggers: dict[str, Logger] = {}
_sync_loggers: dict[str, Logger] = {}


def _get_log_file() -> str:
    return str(Path("logs") / "app.log")


def _flush_all_loggers() -> None:
    for logger in list(_loggers.values()):
        logger.flush()
    for logger in list(_sync_loggers.values()):
        logger.flush()


atexit.register(_flush_all_loggers)


def get_logger(name: str) -> Logger:
    """Get or create a logger that writes in the background when an event loop exists."""
    if name not in _loggers:
        _loggers[name] = Logger(name=name, log_file=_get_log_file(), async_mode=True)
    return _loggers[name]


def get_sync_logger(name: str) -> Logger:
    """Get or create a logger that writes to file immediately."""
    if name not in _sync_loggers:
        _sync_loggers[name] = Logger(name=name, log_file=_get_log_file(), async_mode=False)
    return _sync_loggers[name]


def hard_log(message: str, log_file: str = "logs/app.log") -> None:
    """Write directly to a log file immediately."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as file:
        file.write(message)
        if not message.endswith("\n"):
            file.write("\n")

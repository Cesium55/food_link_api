import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime
from config import settings
from typing import Optional


class AsyncLogger:
    """Async logger that writes logs to file asynchronously using aiofiles"""
    
    def __init__(self, name: str, log_file: str):
        self.name = name
        self.log_file = log_file
        self._queue = asyncio.Queue()
        self._task = None
        self._log_level = getattr(settings, 'log_level', 'INFO').upper()
        
        # Create log directory if it doesn't exist
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    async def _writer(self):
        """Async writer task that writes logs to file using aiofiles"""
        async with aiofiles.open(self.log_file, 'a', encoding='utf-8') as f:
            while True:
                try:
                    level, message, extra = await self._queue.get()
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_message = f"{timestamp} - {self.name} - {level} - {message}"
                    if extra:
                        log_message += f" - {extra}"
                    log_message += "\n"
                    await f.write(log_message)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error in async logger: {e}")
    
    async def _log(self, level: str, message: str, extra: Optional[dict] = None):
        """Internal logging method"""
        if self._task is None or self._task.done():
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._writer())
        
        extra_str = str(extra) if extra else None
        await self._queue.put((level, message, extra_str))
    
    async def debug(self, message: str, extra: Optional[dict] = None):
        """Log debug message"""
        await self._log('DEBUG', message, extra)
    
    async def info(self, message: str, extra: Optional[dict] = None):
        """Log info message"""
        await self._log('INFO', message, extra)
    
    async def warning(self, message: str, extra: Optional[dict] = None):
        """Log warning message"""
        await self._log('WARNING', message, extra)
    
    async def error(self, message: str, extra: Optional[dict] = None):
        """Log error message"""
        await self._log('ERROR', message, extra)
    
    async def critical(self, message: str, extra: Optional[dict] = None):
        """Log critical message"""
        await self._log('CRITICAL', message, extra)
    
    async def close(self):
        """Close the logger and stop the writer task"""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


_loggers = {}


def get_logger(name: str) -> AsyncLogger:
    """Get or create an async logger"""
    if name not in _loggers:
        log_file = str(Path('logs') / 'app.log')
        _loggers[name] = AsyncLogger(name, log_file)
    return _loggers[name] 
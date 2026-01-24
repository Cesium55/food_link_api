"""
Debug logger for direct file logging (bypasses async logger issues in tests)
"""
from datetime import datetime
from pathlib import Path


LOG_FILE = Path(__file__).parent.parent.parent / "logs" / "debug.log"


def hard_log(message: str, prefix: str = "DEBUG") -> None:
    """
    Write log message directly to file synchronously.
    Bypasses async logger to avoid event loop issues in tests.
    
    Args:
        message: The message to log
        prefix: Optional prefix for the log message (default: "DEBUG")
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    log_message = f"{timestamp} | [{prefix}] {message}\n"
    
    # Create log directory if it doesn't exist
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to file (append mode)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message)
    except Exception as e:
        # Fallback to print if file write fails
        print(f"[HARD_LOG ERROR] {e}: {log_message.strip()}")

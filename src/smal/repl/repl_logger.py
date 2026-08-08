"""Module defining a leveled logging facility for the SMAL REPL.

This is distinct from the stylized `console`/`print_*` helpers on the REPL, which are always shown to the user
regardless of level. `SMALLogger` instead provides standard log levels (debug/info/warning/error/critical), each
routed to both the terminal and a persistent log file with independently configurable thresholds. It attaches
its handlers to the root logger, so it also picks up any bare `logging.debug(...)`/`logging.warning(...)` calls
made elsewhere in SMAL (e.g. in the schema/rule/correction layers), which would otherwise be silently dropped or
dumped unformatted to stderr.
"""

from __future__ import annotations  # Until Python 3.14

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from platformdirs import user_data_dir
from rich.logging import RichHandler

if TYPE_CHECKING:
    from rich.console import Console

DEFAULT_LOG_PATH: Path = Path(user_data_dir(appname="smal", appauthor=False)) / "smal.log"


class SMALLogger:
    """Leveled logging facility that mirrors log records to both the terminal and a persistent log file."""

    def __init__(
        self,
        console: Console,
        log_path: Path | str = DEFAULT_LOG_PATH,
        console_level: int = logging.WARNING,
        file_level: int = logging.DEBUG,
    ) -> None:
        """Initialize the SMAL leveled logger and attach its handlers to the root logger.

        Args:
            console (Console): The Rich console to share with the terminal log handler.
            log_path (Path | str, optional): The filepath to write persistent log records to. Defaults to DEFAULT_LOG_PATH.
            console_level (int, optional): The minimum level of records emitted to the terminal. Defaults to logging.WARNING.
            file_level (int, optional): The minimum level of records emitted to the log file. Defaults to logging.DEBUG.

        """
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_path = log_path

        self._logger = logging.getLogger()
        # The logger's own level acts as a gate before any handler is consulted, so it must be at least as
        # permissive as the most permissive handler for that handler's level to have any effect.
        self._logger.setLevel(min(console_level, file_level))
        # Clear any pre-existing handlers (e.g. the default stderr handler) so records aren't duplicated or
        # dumped unformatted to stderr alongside our own handlers.
        self._logger.handlers.clear()

        console_handler = RichHandler(console=console, markup=False, show_path=False, rich_tracebacks=True)
        console_handler.setLevel(console_level)
        self._logger.addHandler(console_handler)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(file_level)
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        self._logger.addHandler(file_handler)

        self._handlers = [console_handler, file_handler]

    @property
    def log_path(self) -> Path:
        """Get the filepath this logger writes persistent log records to.

        Returns:
            Path: The filepath passed to (or defaulted by) `__init__`.

        """
        return self._log_path

    def close(self) -> None:
        """Detach this logger's handlers from the root logger and close them.

        Without this, the `FileHandler` keeps its log file open for the lifetime of the process, and any
        code that constructs a new `SMALLogger` (e.g. tests, or a future REPL restart) would otherwise keep
        stacking duplicate handlers onto the shared root logger.
        """
        for handler in self._handlers:
            self._logger.removeHandler(handler)
            handler.close()
        self._handlers = []

    def debug(self, message: str, *args: object, **kwargs: object) -> None:
        """Log a debug-level message."""
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: object, **kwargs: object) -> None:
        """Log an info-level message."""
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: object, **kwargs: object) -> None:
        """Log a warning-level message."""
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: object, **kwargs: object) -> None:
        """Log an error-level message."""
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: object, **kwargs: object) -> None:
        """Log a critical-level message."""
        self._logger.critical(message, *args, **kwargs)

"""Persistent rotating log for v3 services."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class AppLog:
    def __init__(self, directory=None):
        base = Path(directory) if directory else Path.home() / ".pyobd" / "logs"
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / "pyobd-v3.log"
        self._logger = logging.getLogger("pyobd.v3")
        self._logger.setLevel(logging.INFO)
        if not any(
            isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename) == self.path
            for handler in self._logger.handlers
        ):
            handler = RotatingFileHandler(
                self.path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"
            ))
            self._logger.addHandler(handler)

    def info(self, message):
        self._logger.info(str(message))

    def error(self, message):
        self._logger.error(str(message))


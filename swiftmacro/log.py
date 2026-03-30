# swiftmacro/log.py
"""Central logging factory for SwiftMacro."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under swiftmacro.<name>."""
    return logging.getLogger(f"swiftmacro.{name}")


def configure_logging(profiles_dir: str) -> None:
    """Configure the root swiftmacro logger.

    Production mode (sys.stdout is None — .pyw / PyInstaller --noconsole):
        Rotating file handler → <profiles_dir>/swiftmacro.log, level INFO.
    Development mode (all other cases):
        basicConfig to stderr, level DEBUG.
    """
    import sys

    root = logging.getLogger("swiftmacro")
    root.setLevel(logging.DEBUG)

    if sys.stdout is None:
        # Production: write to rotating log file
        log_path = os.path.join(profiles_dir, "swiftmacro.log")
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
    else:
        # Development: log to console
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s %(name)s: %(message)s",
        )

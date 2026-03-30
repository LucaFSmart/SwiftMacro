"""Tests for swiftmacro/log.py."""
import logging
import sys
from pathlib import Path
from unittest.mock import patch

from swiftmacro.log import configure_logging, get_logger


def _clear_swiftmacro_handlers():
    """Remove all handlers from the swiftmacro logger between tests."""
    root = logging.getLogger("swiftmacro")
    for h in list(root.handlers):
        root.removeHandler(h)


def test_get_logger_returns_namespaced_logger():
    logger = get_logger("profile_store")
    assert logger.name == "swiftmacro.profile_store"


def test_get_logger_is_a_logger_instance():
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)


def test_configure_logging_dev_mode_adds_stream_handler(tmp_path):
    _clear_swiftmacro_handlers()
    configure_logging(str(tmp_path))
    root = logging.getLogger("swiftmacro")
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)
    _clear_swiftmacro_handlers()


def test_configure_logging_prod_mode_adds_file_handler(tmp_path):
    _clear_swiftmacro_handlers()
    with patch.object(sys, "stdout", None):
        configure_logging(str(tmp_path))
    root = logging.getLogger("swiftmacro")
    assert len(root.handlers) == 1
    from logging.handlers import RotatingFileHandler
    assert isinstance(root.handlers[0], RotatingFileHandler)
    # RotatingFileHandler may or may not create the file on init depending on the platform;
    # the important thing is that the handler was added with the correct type and path.
    assert root.handlers[0].baseFilename == str(tmp_path / "swiftmacro.log")
    _clear_swiftmacro_handlers()


def test_configure_logging_is_idempotent(tmp_path):
    _clear_swiftmacro_handlers()
    configure_logging(str(tmp_path))
    configure_logging(str(tmp_path))
    root = logging.getLogger("swiftmacro")
    assert len(root.handlers) == 1, "Second call should not add a second handler"
    _clear_swiftmacro_handlers()

import logging
import os

from notifier.logging_setup import setup_logging, LOG_DIR, LOG_FILE


def test_setup_logging_creates_log_directory():
    setup_logging()
    assert os.path.isdir(LOG_DIR)


def test_setup_logging_attaches_stream_and_file_handlers():
    logger = setup_logging()
    handler_types = {type(h).__name__ for h in logger.handlers}
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" in handler_types


def test_setup_logging_returns_named_logger():
    logger = setup_logging()
    assert logger.name == "tg-notifier"
    assert logger.level == logging.INFO


def test_log_file_path_is_inside_logs_directory():
    assert LOG_FILE.startswith(LOG_DIR)
